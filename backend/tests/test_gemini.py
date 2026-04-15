"""
Tests for Gemini message generation service and GET /api/alerts/{id}/message endpoint.
Gemini API calls are mocked — no real API key needed.
"""
from unittest.mock import patch
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.alert import Alert
from backend.app.models.enums import AlertPriority, AlertStatus, AlertType, MessageTone
from backend.app.models.user import User
from backend.app.models.user_preferences import UserPreferences
from backend.app.services.gemini import _build_prompt, generate_support_message

from .conftest import FakeResult


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fake session
# ---------------------------------------------------------------------------

class FakeMessageSession:
    def __init__(self, alert=None, prefs=None):
        self._alert = alert
        self._prefs = prefs
        self.committed = False

    def get(self, _model, pk):
        if self._alert and str(self._alert.id) == str(pk):
            return self._alert
        return None

    def execute(self, _stmt):
        return FakeResult(self._prefs)

    def commit(self):
        self.committed = True


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


def _make_alert(user_id, alert_type=AlertType.price_drop, generated_messages=None):
    return Alert(
        id=uuid4(),
        user_id=user_id,
        alert_type=alert_type,
        status=AlertStatus.new,
        priority=AlertPriority.high,
        title="Price drop on Sony Headphones",
        body="Sony WH-1000XM5 dropped from $349.99 to $299.99.",
        estimated_savings=50.0,
        generated_messages=generated_messages,
        evidence={"paid_price": 349.99, "current_price": 299.99, "price_delta": 50.0},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_prefs(user_id, tone=MessageTone.polite):
    p = UserPreferences(
        id=uuid4(),
        user_id=user_id,
        min_savings_threshold=10.0,
        notify_price_drop=True,
        notify_delivery_anomaly=True,
        push_notifications_enabled=False,
        preferred_message_tone=tone,
        monitored_retailers=[],
    )
    return p


def _make_client(session, user) -> TestClient:
    app.dependency_overrides[get_db] = lambda: (yield session)
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


# ---------------------------------------------------------------------------
# _build_prompt tests
# ---------------------------------------------------------------------------

def test_build_prompt_price_drop_includes_prices():
    user = _make_user()
    alert = _make_alert(user.id)
    prompt = _build_prompt(alert, MessageTone.polite)
    assert "349.99" in prompt
    assert "299.99" in prompt
    assert "50.00" in prompt


def test_build_prompt_price_drop_includes_tone():
    user = _make_user()
    alert = _make_alert(user.id)
    polite_prompt = _build_prompt(alert, MessageTone.polite)
    firm_prompt = _build_prompt(alert, MessageTone.firm)
    assert polite_prompt != firm_prompt
    assert "polite" in polite_prompt.lower() or "appreciative" in polite_prompt.lower()
    assert "firm" in firm_prompt.lower() or "assertive" in firm_prompt.lower()


def test_build_prompt_delivery_anomaly():
    user = _make_user()
    alert = _make_alert(user.id, alert_type=AlertType.delivery_anomaly)
    alert.body = "Your delivery date slipped by 2 days."
    prompt = _build_prompt(alert, MessageTone.concise)
    assert "delivery" in prompt.lower()
    assert "concise" in prompt.lower() or "short" in prompt.lower()


def test_build_prompt_no_placeholder_brackets():
    user = _make_user()
    alert = _make_alert(user.id)
    prompt = _build_prompt(alert, MessageTone.polite)
    assert "Do not include placeholder brackets" in prompt


# ---------------------------------------------------------------------------
# generate_support_message tests
# ---------------------------------------------------------------------------

def test_generate_support_message_raises_without_api_key():
    user = _make_user()
    alert = _make_alert(user.id)
    with patch(
        "backend.app.services.gemini.generate_cached_gemini_text",
        side_effect=RuntimeError("GEMINI_API_KEY is not configured."),
    ):
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not configured"):
            generate_support_message(alert, MessageTone.polite)


def test_generate_support_message_returns_text():
    user = _make_user()
    alert = _make_alert(user.id)
    with patch(
        "backend.app.services.gemini.generate_cached_gemini_text",
        return_value="Dear Customer Support, I would like to request a price match.",
    ):
        result = generate_support_message(alert, MessageTone.polite)
        assert result == "Dear Customer Support, I would like to request a price match."


def test_generate_support_message_wraps_api_error():
    user = _make_user()
    alert = _make_alert(user.id)
    with patch(
        "backend.app.services.gemini.generate_cached_gemini_text",
        side_effect=Exception("API error"),
    ):
        with pytest.raises(RuntimeError, match="Failed to generate message"):
            generate_support_message(alert, MessageTone.polite)


# ---------------------------------------------------------------------------
# GET /api/alerts/{id}/message endpoint tests
# ---------------------------------------------------------------------------

def test_get_message_returns_generated_message():
    user = _make_user()
    alert = _make_alert(user.id)
    session = FakeMessageSession(alert=alert, prefs=_make_prefs(user.id))
    client = _make_client(session, user)

    with patch("backend.app.api.alerts.generate_support_message", return_value="Please match the price."):
        resp = client.get(f"/api/alerts/{alert.id}/message")

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Please match the price."
    assert data["tone"] == "polite"
    assert data["cached"] is False


def test_get_message_uses_user_preferred_tone():
    user = _make_user()
    alert = _make_alert(user.id)
    session = FakeMessageSession(alert=alert, prefs=_make_prefs(user.id, tone=MessageTone.firm))
    client = _make_client(session, user)

    with patch("backend.app.api.alerts.generate_support_message", return_value="I demand a price match.") as mock_gen:
        resp = client.get(f"/api/alerts/{alert.id}/message")

    assert resp.status_code == 200
    assert resp.json()["tone"] == "firm"
    mock_gen.assert_called_once_with(alert, MessageTone.firm)


def test_get_message_tone_query_param_overrides_preference():
    user = _make_user()
    alert = _make_alert(user.id)
    session = FakeMessageSession(alert=alert, prefs=_make_prefs(user.id, tone=MessageTone.firm))
    client = _make_client(session, user)

    with patch("backend.app.api.alerts.generate_support_message", return_value="Hi.") as mock_gen:
        resp = client.get(f"/api/alerts/{alert.id}/message?tone=concise")

    assert resp.status_code == 200
    assert resp.json()["tone"] == "concise"
    mock_gen.assert_called_once_with(alert, MessageTone.concise)


def test_get_message_returns_cached_if_available():
    user = _make_user()
    alert = _make_alert(user.id, generated_messages={"polite": "Cached message here."})
    session = FakeMessageSession(alert=alert, prefs=_make_prefs(user.id))
    client = _make_client(session, user)

    with patch("backend.app.api.alerts.generate_support_message") as mock_gen:
        resp = client.get(f"/api/alerts/{alert.id}/message")

    assert resp.status_code == 200
    assert resp.json()["message"] == "Cached message here."
    assert resp.json()["cached"] is True
    mock_gen.assert_not_called()


def test_get_message_caches_new_message():
    user = _make_user()
    alert = _make_alert(user.id)
    session = FakeMessageSession(alert=alert, prefs=_make_prefs(user.id))
    client = _make_client(session, user)

    with patch("backend.app.api.alerts.generate_support_message", return_value="New message."):
        client.get(f"/api/alerts/{alert.id}/message")

    assert alert.generated_messages == {"polite": "New message."}
    assert session.committed is True


def test_get_message_not_found_returns_404():
    user = _make_user()
    session = FakeMessageSession(alert=None)
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{uuid4()}/message")
    assert resp.status_code == 404


def test_get_message_other_users_alert_returns_404():
    user = _make_user()
    other_alert = _make_alert(uuid4())  # belongs to different user
    session = FakeMessageSession(alert=other_alert)
    client = _make_client(session, user)

    resp = client.get(f"/api/alerts/{other_alert.id}/message")
    assert resp.status_code == 404


def test_get_message_gemini_unavailable_returns_fallback():
    user = _make_user()
    alert = _make_alert(user.id)
    session = FakeMessageSession(alert=alert, prefs=_make_prefs(user.id))
    client = _make_client(session, user)

    with patch("backend.app.api.alerts.generate_support_message", side_effect=RuntimeError("GEMINI_API_KEY is not configured.")):
        resp = client.get(f"/api/alerts/{alert.id}/message")

    assert resp.status_code == 200
    data = resp.json()
    assert data["fallback"] is True
    assert len(data["message"]) > 0
    assert data["cached"] is False
