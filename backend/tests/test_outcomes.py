"""
Tests for POST /api/outcomes.
Uses TestClient + dependency_overrides, no real DB.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.alert import Alert
from backend.app.models.enums import ActionTaken, AlertStatus, AlertType, AlertPriority
from backend.app.models.order_item import OrderItem
from backend.app.models.outcome_log import OutcomeLog
from backend.app.models.user import User


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fake session
# ---------------------------------------------------------------------------

class FakeOutcomesSession:
    def __init__(self, alert_by_id=None, item_by_id=None):
        self._alert_by_id = alert_by_id or {}
        self._item_by_id = item_by_id or {}
        self.added = []
        self.committed = False

    def get(self, model, pk):
        if model is Alert:
            return self._alert_by_id.get(str(pk))
        if model is OrderItem:
            return self._item_by_id.get(str(pk))
        return None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        from datetime import datetime, timezone
        if obj.id is None:
            obj.id = uuid4()
        if obj.logged_at is None:
            obj.logged_at = datetime.now(timezone.utc)


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


def _make_alert(user_id) -> Alert:
    return Alert(
        id=uuid4(),
        user_id=user_id,
        order_id=uuid4(),
        order_item_id=uuid4(),
        alert_type=AlertType.price_drop,
        status=AlertStatus.new,
        priority=AlertPriority.high,
        title="Price dropped",
        body="Item is cheaper now.",
    )


def _make_order_item(user_id) -> OrderItem:
    return OrderItem(
        id=uuid4(),
        order_id=uuid4(),
        user_id=user_id,
        product_name="Test Product",
        quantity=1,
        paid_price=100.0,
        current_price=100.0,
        is_monitoring_active=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_log_outcome_no_refs_returns_201():
    user = _make_user()
    db = FakeOutcomesSession()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    client = TestClient(app)
    resp = client.post("/api/outcomes", json={
        "action_taken": "ignored",
        "recovered_value": None,
        "was_successful": None,
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data["action_taken"] == "ignored"
    assert data["user_id"] == str(user.id)
    assert data["alert_id"] is None
    assert data["order_item_id"] is None
    assert db.committed is True
    assert len(db.added) == 1


def test_log_outcome_with_alert_and_item():
    user = _make_user()
    alert = _make_alert(user.id)
    item = _make_order_item(user.id)
    db = FakeOutcomesSession(
        alert_by_id={str(alert.id): alert},
        item_by_id={str(item.id): item},
    )
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    client = TestClient(app)
    resp = client.post("/api/outcomes", json={
        "alert_id": str(alert.id),
        "order_item_id": str(item.id),
        "action_taken": "price_matched",
        "recovered_value": 15.50,
        "was_successful": True,
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data["action_taken"] == "price_matched"
    assert data["recovered_value"] == 15.50
    assert data["was_successful"] is True
    assert data["alert_id"] == str(alert.id)
    assert data["order_item_id"] == str(item.id)


def test_log_outcome_unknown_alert_returns_404():
    user = _make_user()
    db = FakeOutcomesSession()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    client = TestClient(app)
    resp = client.post("/api/outcomes", json={
        "alert_id": str(uuid4()),
        "action_taken": "price_matched",
    })

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Alert not found"


def test_log_outcome_alert_belonging_to_other_user_returns_404():
    user = _make_user()
    other_alert = _make_alert(uuid4())  # belongs to a different user
    db = FakeOutcomesSession(alert_by_id={str(other_alert.id): other_alert})
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    client = TestClient(app)
    resp = client.post("/api/outcomes", json={
        "alert_id": str(other_alert.id),
        "action_taken": "price_matched",
    })

    assert resp.status_code == 404


def test_log_outcome_unknown_order_item_returns_404():
    user = _make_user()
    db = FakeOutcomesSession()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    client = TestClient(app)
    resp = client.post("/api/outcomes", json={
        "order_item_id": str(uuid4()),
        "action_taken": "returned_and_rebought",
    })

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Order item not found"


def test_log_outcome_order_item_belonging_to_other_user_returns_404():
    user = _make_user()
    other_item = _make_order_item(uuid4())  # belongs to a different user
    db = FakeOutcomesSession(item_by_id={str(other_item.id): other_item})
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    client = TestClient(app)
    resp = client.post("/api/outcomes", json={
        "order_item_id": str(other_item.id),
        "action_taken": "returned_and_rebought",
    })

    assert resp.status_code == 404


def test_log_outcome_with_notes_and_failure_reason():
    user = _make_user()
    db = FakeOutcomesSession()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    client = TestClient(app)
    resp = client.post("/api/outcomes", json={
        "action_taken": "price_matched",
        "was_successful": False,
        "failure_reason": "Store denied price match",
        "notes": "Tried in store, manager refused.",
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data["was_successful"] is False
    assert data["failure_reason"] == "Store denied price match"
    assert data["notes"] == "Tried in store, manager refused."
