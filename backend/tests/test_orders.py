"""
Unit tests for POST /api/orders (FR-3 order ingestion, FR-4 de-duplication,
return-window deadline calculation).
Uses the FakeSession pattern — no real database required.
"""
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.api.deps import get_current_user, get_db
from backend.app.api.orders import OrderIngest, compute_return_deadline, find_or_create_order
from backend.app.main import app
from backend.app.models.enums import OrderStatus
from backend.app.models.order import Order
from backend.app.models.order_item import OrderItem
from backend.app.models.user import User


# ---------------------------------------------------------------------------
# Fake session
# ---------------------------------------------------------------------------

class FakeOrderSession:
    def __init__(self, existing_order=None):
        self._order = existing_order
        self.added: list = []
        self.deleted: list = []
        self.committed = False

    def query(self, model):
        if model is Order:
            return _FakeOrderQuery(self._order)
        if model is OrderItem:
            return _FakeItemQuery(self)
        return _FakeOrderQuery(None)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, Order):
            self._order = obj

    def flush(self):
        if isinstance(self._order, Order) and not self._order.id:
            self._order.id = uuid4()

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        now = datetime.now(timezone.utc)
        if isinstance(obj, Order):
            if not obj.id:
                obj.id = uuid4()
            if obj.created_at is None:
                obj.created_at = now
            if obj.updated_at is None:
                obj.updated_at = now
            items = [a for a in self.added if isinstance(a, OrderItem)]
            for item in items:
                if not item.id:
                    item.id = uuid4()
                if item.is_monitoring_active is None:
                    item.is_monitoring_active = True
                if item.quantity is None:
                    item.quantity = 1
                if item.created_at is None:
                    item.created_at = now
                if item.updated_at is None:
                    item.updated_at = now
            obj.items = items


class _FakeOrderQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *_args):
        return self

    def first(self):
        return self._result

    def delete(self):
        pass


class _FakeItemQuery:
    def __init__(self, session):
        self._session = session

    def filter(self, *_args):
        return self

    def delete(self):
        self._session.deleted.append("items")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        password_hash="hash",
        is_active=True,
        is_verified=False,
    )


def _make_order(user: User) -> Order:
    order = Order(
        id=uuid4(),
        user_id=user.id,
        retailer="amazon",
        retailer_order_id="112-1234567-1234567",
        order_status=OrderStatus.pending,
        order_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        subtotal=99.99,
        currency="USD",
        price_match_eligible=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    order.items = []
    return order


def _make_client(session: FakeOrderSession, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: (yield session)
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


_MINIMAL_BODY = {
    "retailer": "amazon",
    "retailer_order_id": "112-1234567-1234567",
    "order_status": "pending",
    "order_date": "2024-01-15T00:00:00Z",
    "subtotal": 99.99,
}


# ---------------------------------------------------------------------------
# find_or_create_order unit tests (dedup helper, no HTTP)
# ---------------------------------------------------------------------------

def test_find_or_create_returns_new_when_no_match():
    user = _make_user()
    session = FakeOrderSession(existing_order=None)

    order, is_new = find_or_create_order(session, user.id, "amazon", "112-0000001-0000001")

    assert is_new is True
    assert order in session.added


def test_find_or_create_returns_existing_when_match():
    user = _make_user()
    existing = _make_order(user)
    session = FakeOrderSession(existing_order=existing)

    order, is_new = find_or_create_order(
        session, user.id, existing.retailer, existing.retailer_order_id
    )

    assert is_new is False
    assert order is existing
    assert order not in session.added


def test_find_or_create_does_not_add_duplicate_to_session():
    user = _make_user()
    existing = _make_order(user)
    session = FakeOrderSession(existing_order=existing)

    find_or_create_order(session, user.id, existing.retailer, existing.retailer_order_id)

    assert len(session.added) == 0


# ---------------------------------------------------------------------------
# Input normalization (FR-4)
# ---------------------------------------------------------------------------

def test_retailer_is_lowercased():
    parsed = OrderIngest(
        retailer="AMAZON",
        retailer_order_id="112-0000001-0000001",
        order_status=OrderStatus.pending,
        order_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        subtotal=10.0,
    )
    assert parsed.retailer == "amazon"


def test_retailer_whitespace_is_stripped():
    parsed = OrderIngest(
        retailer="  target  ",
        retailer_order_id="100-9876543-9876543",
        order_status=OrderStatus.pending,
        order_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        subtotal=10.0,
    )
    assert parsed.retailer == "target"


def test_order_id_whitespace_is_stripped():
    parsed = OrderIngest(
        retailer="amazon",
        retailer_order_id="  112-0000001-0000001  ",
        order_status=OrderStatus.pending,
        order_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        subtotal=10.0,
    )
    assert parsed.retailer_order_id == "112-0000001-0000001"


# ---------------------------------------------------------------------------
# HTTP status codes (201 on create, 200 on update)
# ---------------------------------------------------------------------------

def test_new_order_returns_201():
    user = _make_user()
    session = FakeOrderSession(existing_order=None)
    client = _make_client(session, user)

    resp = client.post("/api/orders", json=_MINIMAL_BODY)

    assert resp.status_code == 201


def test_existing_order_returns_200():
    user = _make_user()
    existing = _make_order(user)
    session = FakeOrderSession(existing_order=existing)
    client = _make_client(session, user)

    resp = client.post("/api/orders", json=_MINIMAL_BODY)

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Core ingestion behaviour
# ---------------------------------------------------------------------------

def test_create_order_stores_correct_fields():
    user = _make_user()
    session = FakeOrderSession(existing_order=None)
    client = _make_client(session, user)

    resp = client.post("/api/orders", json=_MINIMAL_BODY)

    data = resp.json()
    assert data["retailer"] == "amazon"
    assert data["retailer_order_id"] == "112-1234567-1234567"
    assert data["order_status"] == "pending"
    assert data["subtotal"] == 99.99
    assert data["currency"] == "USD"
    assert data["user_id"] == str(user.id)


def test_create_order_with_items():
    user = _make_user()
    session = FakeOrderSession(existing_order=None)
    client = _make_client(session, user)

    body = {
        **_MINIMAL_BODY,
        "items": [
            {"product_name": "Running Shoes", "product_url": "https://amazon.com/dp/B001", "paid_price": 99.99},
            {"product_name": "Socks", "product_url": "https://amazon.com/dp/B002", "paid_price": 9.99, "quantity": 3},
        ],
    }

    resp = client.post("/api/orders", json=body)

    assert resp.status_code == 201
    items_added = [a for a in session.added if isinstance(a, OrderItem)]
    assert len(items_added) == 2
    assert items_added[0].product_name == "Running Shoes"
    assert items_added[1].paid_price == 9.99


def test_create_order_item_inherits_user_id():
    user = _make_user()
    session = FakeOrderSession(existing_order=None)
    client = _make_client(session, user)

    body = {**_MINIMAL_BODY, "items": [{"product_name": "Widget", "product_url": "https://amazon.com/dp/X", "paid_price": 5.0}]}

    client.post("/api/orders", json=body)

    item = next(a for a in session.added if isinstance(a, OrderItem))
    assert item.user_id == user.id


def test_upsert_updates_existing_order():
    user = _make_user()
    existing = _make_order(user)
    existing.order_status = OrderStatus.pending
    session = FakeOrderSession(existing_order=existing)
    client = _make_client(session, user)

    body = {**_MINIMAL_BODY, "order_status": "shipped", "tracking_number": "1Z999AA1"}

    resp = client.post("/api/orders", json=body)

    assert resp.status_code == 200
    assert existing.order_status == OrderStatus.shipped
    assert existing.tracking_number == "1Z999AA1"
    assert session.committed is True


def test_upsert_replaces_items():
    user = _make_user()
    existing = _make_order(user)
    session = FakeOrderSession(existing_order=existing)
    client = _make_client(session, user)

    body = {**_MINIMAL_BODY, "items": [{"product_name": "New Item", "product_url": "https://amazon.com/dp/N", "paid_price": 20.0}]}

    resp = client.post("/api/orders", json=body)

    assert resp.status_code == 200
    assert "items" in session.deleted
    new_items = [a for a in session.added if isinstance(a, OrderItem)]
    assert len(new_items) == 1
    assert new_items[0].product_name == "New Item"


def test_no_items_body_creates_order_with_empty_items():
    user = _make_user()
    session = FakeOrderSession(existing_order=None)
    client = _make_client(session, user)

    resp = client.post("/api/orders", json=_MINIMAL_BODY)

    assert resp.status_code == 201
    assert resp.json()["items"] == []


# ---------------------------------------------------------------------------
# Return-window deadline calculation (pure function)
# ---------------------------------------------------------------------------

def test_compute_deadline_from_window():
    result = compute_return_deadline(
        order_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        return_window_days=30,
        explicit_deadline=None,
    )
    assert result == date(2024, 1, 31)


def test_compute_deadline_explicit_overrides_window():
    explicit = date(2024, 2, 14)
    result = compute_return_deadline(
        order_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        return_window_days=30,
        explicit_deadline=explicit,
    )
    assert result == explicit


def test_compute_deadline_no_window_returns_none():
    result = compute_return_deadline(
        order_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        return_window_days=None,
        explicit_deadline=None,
    )
    assert result is None


def test_compute_deadline_zero_day_window():
    result = compute_return_deadline(
        order_date=datetime(2024, 3, 15, tzinfo=timezone.utc),
        return_window_days=0,
        explicit_deadline=None,
    )
    assert result == date(2024, 3, 15)


def test_compute_deadline_accepts_date_object():
    """order_date may already be a date rather than a datetime."""
    result = compute_return_deadline(
        order_date=date(2024, 6, 1),
        return_window_days=15,
        explicit_deadline=None,
    )
    assert result == date(2024, 6, 16)


# ---------------------------------------------------------------------------
# Return-window via HTTP endpoint
# ---------------------------------------------------------------------------

def test_ingest_computes_deadline_from_window():
    user = _make_user()
    session = FakeOrderSession(existing_order=None)
    client = _make_client(session, user)

    body = {**_MINIMAL_BODY, "return_window_days": 30}

    resp = client.post("/api/orders", json=body)

    assert resp.status_code == 201
    # order_date is 2024-01-15, +30 days = 2024-02-14
    assert resp.json()["return_deadline"] == "2024-02-14"


def test_ingest_explicit_deadline_not_overwritten():
    user = _make_user()
    session = FakeOrderSession(existing_order=None)
    client = _make_client(session, user)

    body = {**_MINIMAL_BODY, "return_window_days": 30, "return_deadline": "2024-03-01"}

    resp = client.post("/api/orders", json=body)

    assert resp.status_code == 201
    assert resp.json()["return_deadline"] == "2024-03-01"


def test_ingest_no_window_no_deadline():
    user = _make_user()
    session = FakeOrderSession(existing_order=None)
    client = _make_client(session, user)

    resp = client.post("/api/orders", json=_MINIMAL_BODY)

    assert resp.status_code == 201
    assert resp.json()["return_deadline"] is None
