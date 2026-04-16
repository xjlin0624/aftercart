"""
Unit tests for /api/prices endpoints.
Uses the FakeSession pattern - no real database required.
"""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import backend.app.api.prices as prices_module
from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.alert import Alert
from backend.app.models.enums import OrderStatus, SnapshotSource
from backend.app.models.order import Order
from backend.app.models.order_item import OrderItem
from backend.app.models.price_snapshot import PriceSnapshot
from backend.app.models.user import User
from backend.app.models.user_preferences import UserPreferences


class FakePricesSession:
    def __init__(self, item: OrderItem | None, snapshots: list[PriceSnapshot] | None = None):
        self._item = item
        self._snapshots = snapshots or []

    def get(self, model, pk):
        if model is OrderItem:
            return self._item if self._item and str(self._item.id) == str(pk) else None
        return None

    def query(self, model):
        if model is PriceSnapshot:
            return _FakeSnapshotQuery(self._snapshots)
        return _FakeSnapshotQuery([])


class FakeCaptureSession:
    def __init__(self):
        self.added = []
        self.committed = False
        self.flushed = False

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.committed = True

    def flush(self):
        self.flushed = True
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = uuid4()


class _FakeSnapshotQuery:
    def __init__(self, snapshots):
        self._snapshots = list(snapshots)

    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def limit(self, n):
        self._snapshots = self._snapshots[:n]
        return self

    def all(self):
        return self._snapshots


def _make_user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        password_hash="hash",
        is_active=True,
        is_verified=False,
    )


def _make_item(user: User) -> OrderItem:
    return OrderItem(
        id=uuid4(),
        order_id=uuid4(),
        user_id=user.id,
        product_name="Widget",
        product_url="https://example.com/item",
        paid_price=99.99,
        is_monitoring_active=True,
    )


def _make_tracked_item(
    user: User,
    *,
    retailer: str = "nike",
    sku: str = "STYLE123",
    product_url: str = "https://www.nike.com/t/air-zoom/STYLE123",
    paid_price: float = 120.0,
) -> OrderItem:
    order = Order(
        id=uuid4(),
        user_id=user.id,
        retailer=retailer,
        retailer_order_id=f"{retailer}-{uuid4()}",
        order_status=OrderStatus.pending,
        order_date=datetime.now(timezone.utc),
        subtotal=paid_price,
        currency="USD",
        price_match_eligible=False,
    )
    return OrderItem(
        id=uuid4(),
        order_id=order.id,
        order=order,
        user_id=user.id,
        product_name="Tracked Item",
        product_url=product_url,
        sku=sku,
        paid_price=paid_price,
        is_monitoring_active=True,
    )


def _make_snapshot(item: OrderItem, scraped_price: float = 79.99) -> PriceSnapshot:
    return PriceSnapshot(
        id=uuid4(),
        order_item_id=item.id,
        scraped_price=scraped_price,
        original_paid_price=item.paid_price,
        currency="USD",
        is_available=True,
        snapshot_source=SnapshotSource.scheduled_job,
        scraped_at=datetime.now(timezone.utc),
    )


def _make_client(session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: (yield session)
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_get_price_history_returns_snapshots():
    user = _make_user()
    item = _make_item(user)
    snapshots = [_make_snapshot(item, 79.99), _make_snapshot(item, 85.00)]
    client = _make_client(FakePricesSession(item, snapshots), user)

    resp = client.get(f"/api/prices/{item.id}/history")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["scraped_price"] == 79.99


def test_get_price_history_empty_returns_empty_list():
    user = _make_user()
    item = _make_item(user)
    client = _make_client(FakePricesSession(item, []), user)

    resp = client.get(f"/api/prices/{item.id}/history")

    assert resp.status_code == 200
    assert resp.json() == []


def test_get_price_history_unknown_item_returns_404():
    user = _make_user()
    client = _make_client(FakePricesSession(None), user)

    resp = client.get(f"/api/prices/{uuid4()}/history")

    assert resp.status_code == 404


def test_get_price_history_other_users_item_returns_404():
    user = _make_user()
    other_user = _make_user()
    item = _make_item(other_user)
    client = _make_client(FakePricesSession(item), user)

    resp = client.get(f"/api/prices/{item.id}/history")

    assert resp.status_code == 404


def test_get_price_history_limit_is_respected():
    user = _make_user()
    item = _make_item(user)
    snapshots = [_make_snapshot(item, float(i)) for i in range(10)]
    client = _make_client(FakePricesSession(item, snapshots), user)

    resp = client.get(f"/api/prices/{item.id}/history?limit=3")

    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_get_price_history_includes_price_delta():
    user = _make_user()
    item = _make_item(user)
    snap = _make_snapshot(item, scraped_price=79.99)
    client = _make_client(FakePricesSession(item, [snap]), user)

    resp = client.get(f"/api/prices/{item.id}/history")

    assert resp.status_code == 200
    assert resp.json()[0]["price_delta"] == 20.0


def test_process_extension_price_capture_creates_snapshot_and_alert():
    user = _make_user()
    item = _make_tracked_item(user)
    prefs = UserPreferences(
        id=uuid4(),
        user_id=user.id,
        min_savings_threshold=10.0,
        notify_price_drop=True,
    )
    session = FakeCaptureSession()
    body = prices_module.PriceCaptureIn(
        retailer="nike",
        product_id="STYLE123",
        product_name="Tracked Item",
        product_url="https://www.nike.com/t/air-zoom/STYLE123",
        source_url="https://www.nike.com/t/air-zoom/STYLE123",
        scraped_price=80.0,
        currency="USD",
    )

    result = prices_module.process_extension_price_capture(
        session=session,
        current_user_id=user.id,
        body=body,
        candidate_lookup=lambda _session, _user_id: [item],
        preferences_lookup=lambda _user_id: prefs,
        existing_alert_lookup=lambda _session, _order_item_id: None,
    )

    assert result.status == "snapshot_created"
    assert result.snapshot_count == 1
    assert result.alert_created_count == 1
    assert result.duplicate_alert_count == 0
    assert item.current_price == 80.0
    assert session.committed is True
    assert any(isinstance(entry, PriceSnapshot) for entry in session.added)
    assert any(isinstance(entry, Alert) for entry in session.added)


def test_process_extension_price_capture_skips_when_no_matching_item():
    user = _make_user()
    item = _make_tracked_item(user, retailer="nike", sku="STYLE123")
    session = FakeCaptureSession()
    body = prices_module.PriceCaptureIn(
        retailer="sephora",
        product_id="P456",
        product_name="Different Product",
        product_url="https://www.sephora.com/product/demo-P456",
        source_url="https://www.sephora.com/product/demo-P456",
        scraped_price=50.0,
    )

    result = prices_module.process_extension_price_capture(
        session=session,
        current_user_id=user.id,
        body=body,
        candidate_lookup=lambda _session, _user_id: [item],
        preferences_lookup=lambda _user_id: None,
        existing_alert_lookup=lambda _session, _order_item_id: None,
    )

    assert result.status == "skipped_no_matching_item"
    assert result.snapshot_count == 0
    assert result.alert_created_count == 0
    assert session.committed is False
    assert session.added == []


def test_capture_extension_price_endpoint_uses_helper(monkeypatch):
    user = _make_user()
    session = FakePricesSession(None, [])
    expected = prices_module.PriceCaptureResult(
        status="snapshot_created",
        retailer="nike",
        matched_order_item_ids=[uuid4()],
        snapshot_count=1,
        alert_created_count=1,
        duplicate_alert_count=0,
    )

    def fake_process(*, session, current_user_id, body):
        assert session is session_ref
        assert current_user_id == user.id
        assert body.retailer == "nike"
        return expected

    session_ref = session
    monkeypatch.setattr(prices_module, "process_extension_price_capture", fake_process)

    client = _make_client(session, user)
    resp = client.post(
        "/api/prices/captures",
        json={
            "retailer": "nike",
            "product_id": "STYLE123",
            "product_url": "https://www.nike.com/t/air-zoom/STYLE123",
            "source_url": "https://www.nike.com/t/air-zoom/STYLE123",
            "scraped_price": 80.0,
            "currency": "USD",
        },
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "snapshot_created"
