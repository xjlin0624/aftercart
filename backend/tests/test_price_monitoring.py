from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from backend.app.models import (
    Alert, AlertPriority, AlertStatus, AlertType,
    EffortLevel, Order, OrderItem, OrderStatus, PriceSnapshot,
    RecommendedAction, UserPreferences,
)
from backend.app.scrapers import PriceCheckResult
from backend.app.tasks.price_monitoring import (
    build_price_drop_alert,
    enqueue_candidate_price_checks,
    process_order_item_price_check,
    should_create_price_drop_alert,
)

from .conftest import FakeSession


def build_order_item(
    *,
    active=True,
    product_url="https://example.com/item",
    retailer="nike",
    paid_price=120.0,
    price_match_eligible=False,
    return_deadline=None,
):
    order = Order(
        id=uuid4(),
        user_id=uuid4(),
        retailer=retailer,
        retailer_order_id=f"order-{uuid4()}",
        order_status=OrderStatus.pending,
        order_date=datetime.now(timezone.utc),
        subtotal=paid_price,
        price_match_eligible=price_match_eligible,
        return_deadline=return_deadline,
    )
    item = OrderItem(
        id=uuid4(),
        order_id=order.id,
        order=order,
        user_id=order.user_id,
        product_name="Tracked Item",
        product_url=product_url,
        quantity=1,
        paid_price=paid_price,
        is_monitoring_active=active,
    )
    return item


def _fake_adapter(scraped_price=79.99):
    class FakeAdapter:
        def fetch_current_price(self, _order_item):
            return PriceCheckResult(
                scraped_price=scraped_price,
                currency="USD",
                is_available=True,
                raw_payload={"source": "fake"},
            )
    return FakeAdapter()


def _prefs(threshold=10.0, notify=True):
    return UserPreferences(
        id=uuid4(),
        user_id=uuid4(),
        min_savings_threshold=threshold,
        notify_price_drop=notify,
    )


def test_enqueue_candidate_price_checks_only_picks_active_items_with_product_url():
    selected = []
    order_items = [
        build_order_item(active=True, product_url="https://example.com/1"),
        build_order_item(active=False, product_url="https://example.com/2"),
        build_order_item(active=True, product_url=""),
        build_order_item(active=True, product_url="https://example.com/3"),
    ]

    queued_ids = enqueue_candidate_price_checks(order_items, batch_size=2, delay_fn=selected.append)

    assert queued_ids == [str(order_items[0].id), str(order_items[3].id)]
    assert selected == queued_ids


def test_process_order_item_price_check_creates_snapshot_and_updates_current_price():
    # paid_price=120, scraped=79.99, delta=40.01 >= default threshold 10 → alert created too
    order_item = build_order_item()
    session = FakeSession(order_item)

    result = process_order_item_price_check(
        session=session,
        order_item_id=str(order_item.id),
        adapter_lookup=lambda _retailer: _fake_adapter(),
        prefs_lookup=lambda _uid: None,
    )

    assert result["status"] == "snapshot_created"
    assert order_item.current_price == 79.99
    assert session.committed is True
    assert result["alert_created"] is True
    assert len(session.added) == 2
    assert isinstance(session.added[0], PriceSnapshot)
    assert isinstance(session.added[1], Alert)


def test_process_order_item_price_check_skips_unsupported_retailer():
    order_item = build_order_item(retailer="amazon")
    session = FakeSession(order_item)

    result = process_order_item_price_check(
        session=session,
        order_item_id=str(order_item.id),
        adapter_lookup=lambda _retailer: None,
    )

    assert result["status"] == "skipped_unsupported_retailer"
    assert session.committed is False
    assert session.added == []


# ---------------------------------------------------------------------------
# should_create_price_drop_alert
# ---------------------------------------------------------------------------

def test_should_create_price_drop_alert_drop_meets_threshold():
    assert should_create_price_drop_alert(
        paid_price=100.0, scraped_price=85.0, threshold=10.0, notify_price_drop=True
    ) is True


def test_should_create_price_drop_alert_drop_exactly_at_threshold():
    assert should_create_price_drop_alert(
        paid_price=100.0, scraped_price=90.0, threshold=10.0, notify_price_drop=True
    ) is True


def test_should_create_price_drop_alert_drop_below_threshold():
    assert should_create_price_drop_alert(
        paid_price=100.0, scraped_price=95.0, threshold=10.0, notify_price_drop=True
    ) is False


def test_should_create_price_drop_alert_notify_false():
    assert should_create_price_drop_alert(
        paid_price=100.0, scraped_price=50.0, threshold=10.0, notify_price_drop=False
    ) is False


def test_should_create_price_drop_alert_price_went_up():
    assert should_create_price_drop_alert(
        paid_price=100.0, scraped_price=110.0, threshold=10.0, notify_price_drop=True
    ) is False


# ---------------------------------------------------------------------------
# build_price_drop_alert
# ---------------------------------------------------------------------------

def _fake_snapshot(order_item, scraped_price):
    return PriceSnapshot(
        id=uuid4(),
        order_item_id=order_item.id,
        scraped_price=scraped_price,
        original_paid_price=order_item.paid_price,
        currency="USD",
        is_available=True,
    )


def test_build_price_drop_alert_price_match_path():
    item = build_order_item(paid_price=100.0, price_match_eligible=True)
    snapshot = _fake_snapshot(item, scraped_price=70.0)
    alert = build_price_drop_alert(item, snapshot, threshold=10.0)

    assert alert.recommended_action == RecommendedAction.price_match
    assert alert.estimated_effort == EffortLevel.low
    assert alert.effort_steps_estimate == 3
    assert alert.estimated_savings == 30.0


def test_build_price_drop_alert_return_and_rebuy_path():
    future_deadline = date.today() + timedelta(days=14)
    item = build_order_item(
        paid_price=100.0,
        price_match_eligible=False,
        return_deadline=future_deadline,
    )
    snapshot = _fake_snapshot(item, scraped_price=70.0)
    alert = build_price_drop_alert(item, snapshot, threshold=10.0)

    assert alert.recommended_action == RecommendedAction.return_and_rebuy
    assert alert.estimated_effort == EffortLevel.medium
    assert alert.effort_steps_estimate == 7
    assert alert.days_remaining_return == 14
    assert alert.action_deadline == future_deadline


def test_build_price_drop_alert_no_action_path():
    past_deadline = date.today() - timedelta(days=1)
    item = build_order_item(
        paid_price=100.0,
        price_match_eligible=False,
        return_deadline=past_deadline,
    )
    snapshot = _fake_snapshot(item, scraped_price=70.0)
    alert = build_price_drop_alert(item, snapshot, threshold=10.0)

    assert alert.recommended_action == RecommendedAction.no_action
    assert alert.estimated_effort == EffortLevel.low
    assert alert.effort_steps_estimate == 0


def test_build_price_drop_alert_priority_high():
    # delta=40, threshold=10 → 40 >= 2*10=20 → high
    item = build_order_item(paid_price=100.0)
    snapshot = _fake_snapshot(item, scraped_price=60.0)
    alert = build_price_drop_alert(item, snapshot, threshold=10.0)

    assert alert.priority == AlertPriority.high


def test_build_price_drop_alert_priority_medium():
    # delta=15, threshold=10 → 15 < 2*10=20 → medium
    item = build_order_item(paid_price=100.0)
    snapshot = _fake_snapshot(item, scraped_price=85.0)
    alert = build_price_drop_alert(item, snapshot, threshold=10.0)

    assert alert.priority == AlertPriority.medium


def test_build_price_drop_alert_fields():
    item = build_order_item(paid_price=100.0)
    snapshot = _fake_snapshot(item, scraped_price=75.0)
    alert = build_price_drop_alert(item, snapshot, threshold=10.0)

    assert alert.alert_type == AlertType.price_drop
    assert alert.status == AlertStatus.new
    assert alert.user_id == item.user_id
    assert alert.order_item_id == item.id
    assert alert.evidence["price_at_purchase"] == 100.0
    assert alert.evidence["price_now"] == 75.0


# ---------------------------------------------------------------------------
# process_order_item_price_check — alert behaviour
# ---------------------------------------------------------------------------

def test_process_order_item_price_check_no_alert_when_drop_below_threshold():
    # scraped=115, paid=120, delta=5 < threshold=10 → no alert
    order_item = build_order_item(paid_price=120.0)
    session = FakeSession(order_item)

    result = process_order_item_price_check(
        session=session,
        order_item_id=str(order_item.id),
        adapter_lookup=lambda _: _fake_adapter(scraped_price=115.0),
        prefs_lookup=lambda _uid: _prefs(threshold=10.0, notify=True),
    )

    assert result["alert_created"] is False
    assert len(session.added) == 1
    assert isinstance(session.added[0], PriceSnapshot)


def test_process_order_item_price_check_no_alert_when_notify_false():
    order_item = build_order_item(paid_price=120.0)
    session = FakeSession(order_item)

    result = process_order_item_price_check(
        session=session,
        order_item_id=str(order_item.id),
        adapter_lookup=lambda _: _fake_adapter(scraped_price=79.99),
        prefs_lookup=lambda _uid: _prefs(threshold=10.0, notify=False),
    )

    assert result["alert_created"] is False
    assert len(session.added) == 1


def test_process_order_item_price_check_alert_respects_custom_threshold():
    # delta=40.01, threshold=50 → no alert
    order_item = build_order_item(paid_price=120.0)
    session = FakeSession(order_item)

    result = process_order_item_price_check(
        session=session,
        order_item_id=str(order_item.id),
        adapter_lookup=lambda _: _fake_adapter(scraped_price=79.99),
        prefs_lookup=lambda _uid: _prefs(threshold=50.0, notify=True),
    )

    assert result["alert_created"] is False


def test_process_order_item_price_check_prefs_lookup_injectable():
    called_with = []

    def fake_prefs(uid):
        called_with.append(uid)
        return _prefs(threshold=10.0, notify=True)

    order_item = build_order_item(paid_price=120.0)
    session = FakeSession(order_item)

    process_order_item_price_check(
        session=session,
        order_item_id=str(order_item.id),
        adapter_lookup=lambda _: _fake_adapter(scraped_price=79.99),
        prefs_lookup=fake_prefs,
    )

    assert called_with == [order_item.user_id]
