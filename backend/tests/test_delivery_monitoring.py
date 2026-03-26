"""
Unit tests for backend/app/tasks/delivery_monitoring.py.

Covers:
- detect_eta_slippage
- detect_stalled_tracking
- build_delivery_anomaly_alert
- process_order_delivery_check
- enqueue_candidate_delivery_checks
Uses FakeSession / injectable lookups — no real DB.
"""
from datetime import date, datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from backend.app.models import Alert, DeliveryEvent
from backend.app.models.enums import (
    AlertStatus, AlertType, DeliveryEventType, OrderStatus,
)
from backend.app.tasks.delivery_monitoring import (
    build_delivery_anomaly_alert,
    detect_eta_slippage,
    detect_stalled_tracking,
    enqueue_candidate_delivery_checks,
    process_order_delivery_check,
)

from .conftest import FakeSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _order(
    *,
    status=OrderStatus.in_transit,
    tracking_number="TRACK123",
    estimated_delivery=None,
    user_id=None,
    retailer_order_id="ORD-001",
):
    o = MagicMock()
    o.id = uuid4()
    o.user_id = user_id or uuid4()
    o.order_status = status
    o.tracking_number = tracking_number
    o.estimated_delivery = estimated_delivery
    o.retailer_order_id = retailer_order_id
    return o


def _prefs(*, notify_delivery_anomaly=True):
    p = MagicMock()
    p.notify_delivery_anomaly = notify_delivery_anomaly
    return p


def _delivery_event(
    *,
    order_id=None,
    event_type=DeliveryEventType.eta_updated,
    previous_eta=None,
    new_eta=None,
    is_anomaly=False,
    scraped_at=None,
    notes=None,
):
    return DeliveryEvent(
        id=uuid4(),
        order_id=order_id or uuid4(),
        event_type=event_type,
        previous_eta=previous_eta,
        new_eta=new_eta,
        is_anomaly=is_anomaly,
        scraped_at=scraped_at or datetime.now(timezone.utc),
        notes=notes,
    )


TODAY = date(2026, 3, 26)


# ---------------------------------------------------------------------------
# detect_eta_slippage
# ---------------------------------------------------------------------------

def test_detect_eta_slippage_slipped_forward_is_anomaly():
    old_eta = date(2026, 3, 20)
    new_eta = date(2026, 3, 25)
    order = _order(estimated_delivery=new_eta)

    event = detect_eta_slippage(order, last_eta=old_eta)

    assert event is not None
    assert event.event_type == DeliveryEventType.eta_updated
    assert event.previous_eta == old_eta
    assert event.new_eta == new_eta
    assert event.is_anomaly is True


def test_detect_eta_slippage_improved_not_anomaly():
    old_eta = date(2026, 3, 30)
    new_eta = date(2026, 3, 27)
    order = _order(estimated_delivery=new_eta)

    event = detect_eta_slippage(order, last_eta=old_eta)

    assert event is not None
    assert event.is_anomaly is False


def test_detect_eta_slippage_no_change_returns_none():
    eta = date(2026, 3, 28)
    order = _order(estimated_delivery=eta)

    event = detect_eta_slippage(order, last_eta=eta)

    assert event is None


def test_detect_eta_slippage_no_baseline_returns_none():
    order = _order(estimated_delivery=date(2026, 3, 28))

    event = detect_eta_slippage(order, last_eta=None)

    assert event is None


def test_detect_eta_slippage_no_current_eta_returns_none():
    order = _order(estimated_delivery=None)

    event = detect_eta_slippage(order, last_eta=date(2026, 3, 20))

    assert event is None


def test_detect_eta_slippage_terminal_order_returns_none():
    order = _order(status=OrderStatus.delivered, estimated_delivery=date(2026, 3, 28))

    event = detect_eta_slippage(order, last_eta=date(2026, 3, 25))

    assert event is None


def test_detect_eta_slippage_cancelled_order_returns_none():
    order = _order(status=OrderStatus.cancelled, estimated_delivery=date(2026, 3, 28))

    event = detect_eta_slippage(order, last_eta=date(2026, 3, 25))

    assert event is None


# ---------------------------------------------------------------------------
# detect_stalled_tracking
# ---------------------------------------------------------------------------

def test_detect_stalled_tracking_stalled_returns_event():
    last_scraped = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)  # 6 days ago
    order = _order()

    event = detect_stalled_tracking(order, last_scraped, None, TODAY, stall_threshold_days=3)

    assert event is not None
    assert event.event_type == DeliveryEventType.tracking_stalled
    assert event.is_anomaly is True


def test_detect_stalled_tracking_recent_event_returns_none():
    last_scraped = datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc)  # 1 day ago
    order = _order()

    event = detect_stalled_tracking(order, last_scraped, None, TODAY, stall_threshold_days=3)

    assert event is None


def test_detect_stalled_tracking_no_baseline_returns_none():
    order = _order()

    event = detect_stalled_tracking(order, None, None, TODAY)

    assert event is None


def test_detect_stalled_tracking_already_stalled_deduplicates():
    last_scraped = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)
    order = _order()

    event = detect_stalled_tracking(order, last_scraped, DeliveryEventType.tracking_stalled, TODAY)

    assert event is None


def test_detect_stalled_tracking_non_in_transit_order_returns_none():
    last_scraped = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)
    order = _order(status=OrderStatus.shipped)

    event = detect_stalled_tracking(order, last_scraped, None, TODAY, stall_threshold_days=3)

    assert event is None


def test_detect_stalled_tracking_no_tracking_number_returns_none():
    last_scraped = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)
    order = _order(tracking_number=None)

    event = detect_stalled_tracking(order, last_scraped, None, TODAY, stall_threshold_days=3)

    assert event is None


def test_detect_stalled_tracking_exactly_at_threshold():
    # Exactly at threshold: (today - scraped).days == stall_threshold_days → stalled
    last_scraped = datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc)  # 3 days ago
    order = _order()

    event = detect_stalled_tracking(order, last_scraped, None, TODAY, stall_threshold_days=3)

    assert event is not None


# ---------------------------------------------------------------------------
# build_delivery_anomaly_alert
# ---------------------------------------------------------------------------

def test_build_delivery_anomaly_alert_eta_updated():
    order = _order()
    event = _delivery_event(
        order_id=order.id,
        event_type=DeliveryEventType.eta_updated,
        previous_eta=date(2026, 3, 20),
        new_eta=date(2026, 3, 25),
        is_anomaly=True,
    )

    alert = build_delivery_anomaly_alert(order, event)

    assert alert.alert_type == AlertType.delivery_anomaly
    assert alert.status == AlertStatus.new
    assert alert.user_id == order.user_id
    assert alert.order_id == order.id
    assert "slipped" in alert.body
    assert "2026-03-20" in alert.body
    assert "2026-03-25" in alert.body


def test_build_delivery_anomaly_alert_tracking_stalled():
    order = _order()
    event = _delivery_event(
        order_id=order.id,
        event_type=DeliveryEventType.tracking_stalled,
        is_anomaly=True,
        notes="No tracking update in 5 day(s) (threshold: 3 day(s)).",
    )

    alert = build_delivery_anomaly_alert(order, event)

    assert alert.alert_type == AlertType.delivery_anomaly
    assert "stalled" in alert.title.lower()
    assert "5 day" in alert.body


def test_build_delivery_anomaly_alert_evidence_fields():
    order = _order()
    event = _delivery_event(
        order_id=order.id,
        event_type=DeliveryEventType.eta_updated,
        previous_eta=date(2026, 3, 20),
        new_eta=date(2026, 3, 25),
        is_anomaly=True,
    )

    alert = build_delivery_anomaly_alert(order, event)

    assert alert.evidence["event_type"] == "eta_updated"
    assert alert.evidence["is_anomaly"] is True
    assert alert.evidence["previous_eta"] == "2026-03-20"
    assert alert.evidence["new_eta"] == "2026-03-25"


# ---------------------------------------------------------------------------
# process_order_delivery_check
# ---------------------------------------------------------------------------

class FakeDeliverySession(FakeSession):
    """FakeSession with configurable get() and lookup results."""

    def __init__(self, order=None):
        super().__init__()
        self._order = order

    def get(self, _model, _pk):
        return self._order


def test_process_skips_missing_order():
    session = FakeDeliverySession(order=None)

    result = process_order_delivery_check(session, uuid4())

    assert result["status"] == "skipped_missing_order"
    assert result["events_created"] == 0


def test_process_skips_terminal_order():
    order = _order(status=OrderStatus.delivered)
    session = FakeDeliverySession(order=order)

    result = process_order_delivery_check(session, order.id)

    assert result["status"] == "skipped_terminal_order"
    assert not session.committed


def test_process_skips_order_without_tracking():
    order = _order(tracking_number=None)
    session = FakeDeliverySession(order=order)

    result = process_order_delivery_check(session, order.id)

    assert result["status"] == "skipped_no_tracking"


def test_process_creates_eta_event_and_alert_when_anomaly():
    order = _order(estimated_delivery=date(2026, 3, 25))
    session = FakeDeliverySession(order=order)

    def last_eta_lookup(_s, _id):
        return date(2026, 3, 20)  # ETA slipped forward

    def last_event_lookup(_s, _id):
        return None, None

    result = process_order_delivery_check(
        session,
        order.id,
        prefs_lookup=lambda _uid: _prefs(notify_delivery_anomaly=True),
        last_eta_lookup=last_eta_lookup,
        last_event_lookup=last_event_lookup,
    )

    assert result["status"] == "checked"
    assert result["events_created"] == 1
    assert result["alert_created"] is True
    assert session.committed is True
    assert any(isinstance(o, DeliveryEvent) for o in session.added)
    assert any(isinstance(o, Alert) for o in session.added)


def test_process_creates_eta_event_no_alert_when_not_anomaly():
    order = _order(estimated_delivery=date(2026, 3, 18))  # improved
    session = FakeDeliverySession(order=order)

    def last_eta_lookup(_s, _id):
        return date(2026, 3, 25)

    def last_event_lookup(_s, _id):
        return None, None

    result = process_order_delivery_check(
        session,
        order.id,
        prefs_lookup=lambda _uid: _prefs(),
        last_eta_lookup=last_eta_lookup,
        last_event_lookup=last_event_lookup,
    )

    assert result["events_created"] == 1
    assert result["alert_created"] is False
    assert not any(isinstance(o, Alert) for o in session.added)


def test_process_creates_stall_event_and_alert():
    order = _order()
    session = FakeDeliverySession(order=order)
    stale_time = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)

    def last_eta_lookup(_s, _id):
        return None  # no ETA baseline

    def last_event_lookup(_s, _id):
        return stale_time, DeliveryEventType.status_changed

    result = process_order_delivery_check(
        session,
        order.id,
        prefs_lookup=lambda _uid: _prefs(),
        last_eta_lookup=last_eta_lookup,
        last_event_lookup=last_event_lookup,
        stall_threshold_days=3,
    )

    assert result["events_created"] == 1
    assert result["alert_created"] is True


def test_process_no_events_does_not_commit():
    order = _order(estimated_delivery=date(2026, 3, 28))
    session = FakeDeliverySession(order=order)
    recent_time = datetime(2026, 3, 26, 10, 0, tzinfo=timezone.utc)

    def last_eta_lookup(_s, _id):
        return date(2026, 3, 28)  # no change

    def last_event_lookup(_s, _id):
        return recent_time, DeliveryEventType.status_changed

    result = process_order_delivery_check(
        session,
        order.id,
        prefs_lookup=lambda _uid: _prefs(),
        last_eta_lookup=last_eta_lookup,
        last_event_lookup=last_event_lookup,
    )

    assert result["events_created"] == 0
    assert session.committed is False


def test_process_suppresses_alert_when_notify_disabled():
    order = _order(estimated_delivery=date(2026, 3, 25))
    session = FakeDeliverySession(order=order)

    def last_eta_lookup(_s, _id):
        return date(2026, 3, 20)

    def last_event_lookup(_s, _id):
        return None, None

    result = process_order_delivery_check(
        session,
        order.id,
        prefs_lookup=lambda _uid: _prefs(notify_delivery_anomaly=False),
        last_eta_lookup=last_eta_lookup,
        last_event_lookup=last_event_lookup,
    )

    assert result["events_created"] == 1
    assert result["alert_created"] is False
    assert not any(isinstance(o, Alert) for o in session.added)


def test_process_both_eta_and_stall_detected():
    # Both events fire, but only one alert is created (eta takes priority; stall skipped).
    order = _order(estimated_delivery=date(2026, 3, 25))
    session = FakeDeliverySession(order=order)
    stale_time = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)

    def last_eta_lookup(_s, _id):
        return date(2026, 3, 20)  # slipped forward

    def last_event_lookup(_s, _id):
        return stale_time, DeliveryEventType.status_changed  # carrier silent for 6 days

    result = process_order_delivery_check(
        session,
        order.id,
        prefs_lookup=lambda _uid: _prefs(),
        last_eta_lookup=last_eta_lookup,
        last_event_lookup=last_event_lookup,
        stall_threshold_days=3,
    )

    assert result["events_created"] == 2
    assert result["alert_created"] is True
    assert sum(1 for o in session.added if isinstance(o, Alert)) == 1


def test_process_skips_eta_alert_when_duplicate_exists():
    order = _order(estimated_delivery=date(2026, 3, 25))
    session = FakeDeliverySession(order=order)
    existing = MagicMock()  # simulates an existing unresolved delivery_anomaly alert

    result = process_order_delivery_check(
        session,
        order.id,
        prefs_lookup=lambda _uid: _prefs(),
        last_eta_lookup=lambda _s, _id: date(2026, 3, 20),
        last_event_lookup=lambda _s, _id: (None, None),
        existing_alert_lookup=lambda _s, _id: existing,
    )

    assert result["alert_created"] is False
    assert result["alert_skipped_duplicate"] is True
    assert not any(isinstance(o, Alert) for o in session.added)


def test_process_skips_stall_alert_when_duplicate_exists():
    order = _order()
    session = FakeDeliverySession(order=order)
    stale_time = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)
    existing = MagicMock()

    result = process_order_delivery_check(
        session,
        order.id,
        prefs_lookup=lambda _uid: _prefs(),
        last_eta_lookup=lambda _s, _id: None,
        last_event_lookup=lambda _s, _id: (stale_time, DeliveryEventType.status_changed),
        existing_alert_lookup=lambda _s, _id: existing,
        stall_threshold_days=3,
    )

    assert result["alert_created"] is False
    assert result["alert_skipped_duplicate"] is True
    assert not any(isinstance(o, Alert) for o in session.added)


# ---------------------------------------------------------------------------
# enqueue_candidate_delivery_checks
# ---------------------------------------------------------------------------

def test_enqueue_skips_terminal_orders():
    orders = [
        _order(status=OrderStatus.delivered),
        _order(status=OrderStatus.cancelled),
        _order(status=OrderStatus.returned),
    ]
    enqueued = []

    result = enqueue_candidate_delivery_checks(orders, delay_fn=enqueued.append)

    assert result == []
    assert enqueued == []


def test_enqueue_skips_orders_without_tracking():
    orders = [_order(tracking_number=None), _order(tracking_number="")]
    enqueued = []

    result = enqueue_candidate_delivery_checks(orders, delay_fn=enqueued.append)

    assert result == []


def test_enqueue_includes_eligible_orders():
    orders = [
        _order(status=OrderStatus.in_transit),
        _order(status=OrderStatus.shipped),
        _order(status=OrderStatus.delivered),  # should be skipped
    ]
    enqueued = []

    result = enqueue_candidate_delivery_checks(orders, delay_fn=enqueued.append)

    assert len(result) == 2
    assert len(enqueued) == 2


def test_enqueue_calls_delay_for_each_eligible():
    order = _order()
    calls = []

    enqueue_candidate_delivery_checks([order], delay_fn=calls.append)

    assert calls == [str(order.id)]
