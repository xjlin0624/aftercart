"""
Tests for GET /api/alerts, GET /api/alerts/{id},
PATCH /api/alerts/{id}/resolve, PATCH /api/alerts/{id}/dismiss,
PATCH /api/alerts/{id}, and GET /api/alerts/{id}/recommendation.
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


_EFFORT_BY_ACTION = {
    RecommendedAction.price_match:    (EffortLevel.low,    3),
    RecommendedAction.return_and_rebuy: (EffortLevel.medium, 7),
    RecommendedAction.no_action:      (EffortLevel.low,    0),
}


def _make_alert(user_id, *, alert_status=AlertStatus.new, action=RecommendedAction.price_match):
    effort, steps = _EFFORT_BY_ACTION[action]
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
        estimated_effort=effort,
        effort_steps_estimate=steps,
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
# GET /api/alerts/{alert_id}
# ---------------------------------------------------------------------------

def test_get_alert_returns_alert():
    user = _make_user()
    alert = _make_alert(user.id)
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{alert.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(alert.id)
    assert data["user_id"] == str(user.id)
    assert data["recommended_action"] == "price_match"


def test_get_alert_not_found_returns_404():
    user = _make_user()
    client = _make_client(FakeAlertsSession(), user)

    resp = client.get(f"/api/alerts/{uuid4()}")

    assert resp.status_code == 404


def test_get_alert_owned_by_other_user_returns_404():
    user = _make_user()
    alert = _make_alert(uuid4())
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{alert.id}")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/alerts/{alert_id}/resolve
# ---------------------------------------------------------------------------

def test_resolve_alert_sets_status_and_resolved_at():
    user = _make_user()
    alert = _make_alert(user.id, alert_status=AlertStatus.new)
    assert alert.resolved_at is None
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.patch(f"/api/alerts/{alert.id}/resolve")

    assert resp.status_code == 200
    assert alert.status == AlertStatus.resolved
    assert alert.resolved_at is not None
    assert session.committed is True


def test_resolve_alert_is_idempotent():
    user = _make_user()
    alert = _make_alert(user.id, alert_status=AlertStatus.resolved)
    original_ts = datetime.now(timezone.utc)
    alert.resolved_at = original_ts
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.patch(f"/api/alerts/{alert.id}/resolve")

    assert resp.status_code == 200
    assert alert.resolved_at == original_ts  # not overwritten


def test_resolve_alert_not_found_returns_404():
    user = _make_user()
    client = _make_client(FakeAlertsSession(), user)

    resp = client.patch(f"/api/alerts/{uuid4()}/resolve")

    assert resp.status_code == 404


def test_resolve_alert_owned_by_other_user_returns_404():
    user = _make_user()
    alert = _make_alert(uuid4())
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.patch(f"/api/alerts/{alert.id}/resolve")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/alerts/{alert_id}/dismiss
# ---------------------------------------------------------------------------

def test_dismiss_alert_sets_status_and_resolved_at():
    user = _make_user()
    alert = _make_alert(user.id, alert_status=AlertStatus.new)
    assert alert.resolved_at is None
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.patch(f"/api/alerts/{alert.id}/dismiss")

    assert resp.status_code == 200
    assert alert.status == AlertStatus.dismissed
    assert alert.resolved_at is not None
    assert session.committed is True


def test_dismiss_alert_is_idempotent():
    user = _make_user()
    alert = _make_alert(user.id, alert_status=AlertStatus.dismissed)
    original_ts = datetime.now(timezone.utc)
    alert.resolved_at = original_ts
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.patch(f"/api/alerts/{alert.id}/dismiss")

    assert resp.status_code == 200
    assert alert.resolved_at == original_ts  # not overwritten


def test_dismiss_alert_not_found_returns_404():
    user = _make_user()
    client = _make_client(FakeAlertsSession(), user)

    resp = client.patch(f"/api/alerts/{uuid4()}/dismiss")

    assert resp.status_code == 404


def test_dismiss_alert_owned_by_other_user_returns_404():
    user = _make_user()
    alert = _make_alert(uuid4())
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.patch(f"/api/alerts/{alert.id}/dismiss")

    assert resp.status_code == 404


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


# ---------------------------------------------------------------------------
# GET /api/alerts/{alert_id}/recommendation
# ---------------------------------------------------------------------------

def test_get_recommendation_returns_explained_payload():
    user = _make_user()
    alert = _make_alert(user.id, action=RecommendedAction.price_match)
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{alert.id}/recommendation")

    assert resp.status_code == 200
    data = resp.json()
    assert data["alert_id"] == str(alert.id)
    assert data["recommended_action"] == "price_match"
    assert data["estimated_savings"] == 30.0
    assert data["estimated_effort"] == "low"
    assert data["effort_steps_estimate"] == 3


def test_get_recommendation_includes_decision_factors():
    user = _make_user()
    alert = _make_alert(user.id, action=RecommendedAction.price_match)
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{alert.id}/recommendation")

    data = resp.json()
    factors = {f["factor"]: f for f in data["decision_factors"]}
    assert "price_match_eligible" in factors
    assert "return_window_open" in factors
    assert factors["price_match_eligible"]["result"] is True
    assert factors["return_window_open"]["result"] is False


def test_get_recommendation_includes_action_steps():
    user = _make_user()
    alert = _make_alert(user.id, action=RecommendedAction.price_match)
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{alert.id}/recommendation")

    data = resp.json()
    assert len(data["action_steps"]) == 3
    assert data["action_steps"][0]["step"] == 1


def test_get_recommendation_return_and_rebuy_factors():
    user = _make_user()
    alert = _make_alert(user.id, action=RecommendedAction.return_and_rebuy)
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{alert.id}/recommendation")

    data = resp.json()
    factors = {f["factor"]: f for f in data["decision_factors"]}
    assert factors["price_match_eligible"]["result"] is False
    assert factors["return_window_open"]["result"] is True
    assert len(data["action_steps"]) == 7


def test_get_recommendation_not_found_returns_404():
    user = _make_user()
    client = _make_client(FakeAlertsSession(), user)

    resp = client.get(f"/api/alerts/{uuid4()}/recommendation")

    assert resp.status_code == 404


def test_get_recommendation_other_user_alert_returns_404():
    user = _make_user()
    other_user_id = uuid4()
    alert = _make_alert(other_user_id)
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{alert.id}/recommendation")

    assert resp.status_code == 404


def test_get_recommendation_no_action_alert_returns_empty_steps():
    user = _make_user()
    alert = _make_alert(user.id, action=RecommendedAction.no_action)
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{alert.id}/recommendation")

    assert resp.status_code == 200
    assert resp.json()["action_steps"] == []


def test_get_recommendation_alert_with_no_recommended_action_returns_422():
    user = _make_user()
    alert = Alert(
        id=uuid4(),
        user_id=user.id,
        order_id=uuid4(),
        order_item_id=uuid4(),
        alert_type=AlertType.price_drop,
        status=AlertStatus.new,
        priority=AlertPriority.medium,
        title="Alert",
        body="Body",
        recommended_action=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session = FakeAlertsSession(alert_by_id={str(alert.id): alert})
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{alert.id}/recommendation")

    assert resp.status_code == 422
