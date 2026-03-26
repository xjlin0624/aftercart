"""
Tests for GET /api/alerts and PATCH /api/alerts/{id}.
Uses TestClient + dependency_overrides, no real DB.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.alert import Alert
from backend.app.models.enums import (
    AlertPriority, AlertStatus, AlertType, EffortLevel, RecommendedAction,
)
from backend.app.models.user import User

from .conftest import FakeResult


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fake session
# ---------------------------------------------------------------------------

class FakeAlertsSession:
    def __init__(self, alerts=None, alert_by_id=None):
        self._alerts = alerts or []
        self._alert_by_id = alert_by_id or {}
        self.committed = False

    def execute(self, _stmt):
        return FakeResult(self._alerts)

    def get(self, _model, pk):
        return self._alert_by_id.get(str(pk))

    def commit(self):
        self.committed = True

    def refresh(self, _obj):
        pass


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


def _make_alert(user_id, *, alert_status=AlertStatus.new, action=RecommendedAction.price_match):
    return Alert(
        id=uuid4(),
        user_id=user_id,
        order_id=uuid4(),
        order_item_id=uuid4(),
        alert_type=AlertType.price_drop,
        status=alert_status,
        priority=AlertPriority.high,
        title="Price drop on Widget",
        body="Widget dropped from $100.00 to $70.00 — you could save $30.00.",
        recommended_action=action,
        estimated_savings=30.0,
        estimated_effort=EffortLevel.low,
        effort_steps_estimate=3,
        recommendation_rationale="Current price $70.00 is $30.00 below your purchase price of $100.00.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_client(session, user) -> TestClient:
    app.dependency_overrides[get_db] = lambda: (yield session)
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/alerts
# ---------------------------------------------------------------------------

def test_list_alerts_returns_user_alerts():
    user = _make_user()
    alerts = [_make_alert(user.id), _make_alert(user.id)]
    client = _make_client(FakeAlertsSession(alerts=alerts), user)

    resp = client.get("/api/alerts")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["recommended_action"] == "price_match"
    assert data[0]["user_id"] == str(user.id)


def test_list_alerts_empty_list():
    user = _make_user()
    client = _make_client(FakeAlertsSession(alerts=[]), user)

    resp = client.get("/api/alerts")

    assert resp.status_code == 200
    assert resp.json() == []


def test_list_alerts_invalid_status_returns_422():
    user = _make_user()
    client = _make_client(FakeAlertsSession(alerts=[]), user)

    resp = client.get("/api/alerts?status=bogus_value")

    assert resp.status_code == 422


def test_list_alerts_status_param_parsed_and_response_returned():
    # Verifies the ?status= enum param is accepted and the response is well-formed.
    # SQL-level filtering is not verifiable without a real DB (FakeAlertsSession
    # ignores the statement), so we confirm the route accepts the param and
    # returns the pre-configured alert correctly.
    user = _make_user()
    alert = _make_alert(user.id, alert_status=AlertStatus.viewed)
    client = _make_client(FakeAlertsSession(alerts=[alert]), user)

    resp = client.get("/api/alerts?status=viewed")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "viewed"


def test_list_alerts_returns_correct_recommendation_fields():
    user = _make_user()
    alert = _make_alert(user.id, action=RecommendedAction.return_and_rebuy)
    client = _make_client(FakeAlertsSession(alerts=[alert]), user)

    resp = client.get("/api/alerts")

    data = resp.json()
    assert data[0]["recommended_action"] == "return_and_rebuy"
    assert data[0]["estimated_savings"] == 30.0
    assert data[0]["priority"] == "high"


# ---------------------------------------------------------------------------
# PATCH /api/alerts/{alert_id}
# ---------------------------------------------------------------------------

def test_patch_alert_updates_status():
    user = _make_user()
    alert = _make_alert(user.id, alert_status=AlertStatus.new)
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.patch(f"/api/alerts/{alert.id}", json={"status": "viewed"})

    assert resp.status_code == 200
    assert alert.status == AlertStatus.viewed
    assert session.committed is True


def test_patch_alert_sets_resolved_at_on_resolve():
    user = _make_user()
    alert = _make_alert(user.id, alert_status=AlertStatus.new)
    assert alert.resolved_at is None
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.patch(f"/api/alerts/{alert.id}", json={"status": "resolved"})

    assert resp.status_code == 200
    assert alert.resolved_at is not None


def test_patch_alert_sets_resolved_at_on_dismiss():
    user = _make_user()
    alert = _make_alert(user.id, alert_status=AlertStatus.new)
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.patch(f"/api/alerts/{alert.id}", json={"status": "dismissed"})

    assert resp.status_code == 200
    assert alert.resolved_at is not None


def test_patch_alert_not_found_returns_404():
    user = _make_user()
    client = _make_client(FakeAlertsSession(), user)

    resp = client.patch(f"/api/alerts/{uuid4()}", json={"status": "viewed"})

    assert resp.status_code == 404


def test_patch_alert_owned_by_other_user_returns_404():
    user = _make_user()
    other_user_id = uuid4()
    alert = _make_alert(other_user_id)
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.patch(f"/api/alerts/{alert.id}", json={"status": "viewed"})

    assert resp.status_code == 404
