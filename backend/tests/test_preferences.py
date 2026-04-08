"""
Unit tests for GET/PATCH /api/users/me/preferences.
Uses the same FakeSession pattern as the rest of the test suite.
"""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.enums import MessageTone
from backend.app.models.user import User
from backend.app.models.user_preferences import UserPreferences


# ---------------------------------------------------------------------------
# Fake session
# ---------------------------------------------------------------------------

class FakePrefsSession:
    def __init__(self, user=None, prefs=None):
        self._user = user
        self._prefs = prefs
        self.added = []
        self.committed = False

    def query(self, model):
        return _FakeQuery(self._prefs if model is UserPreferences else self._user)

    def get(self, _model, pk):
        if self._user and str(self._user.id) == str(pk):
            return self._user
        return None

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, UserPreferences):
            self._prefs = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        now = datetime.now(timezone.utc)
        if isinstance(obj, UserPreferences):
            if not obj.id:
                obj.id = uuid4()
            if obj.updated_at is None:
                obj.updated_at = now
            # Apply column-level defaults not set at construction time
            if obj.min_savings_threshold is None:
                obj.min_savings_threshold = 10.0
            if obj.notify_price_drop is None:
                obj.notify_price_drop = True
            if obj.notify_delivery_anomaly is None:
                obj.notify_delivery_anomaly = True
            if obj.push_notifications_enabled is None:
                obj.push_notifications_enabled = False
            if obj.preferred_message_tone is None:
                obj.preferred_message_tone = MessageTone.polite
            if obj.monitored_retailers is None:
                obj.monitored_retailers = []


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *_args):
        return self

    def first(self):
        return self._result


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


def _make_prefs(user: User) -> UserPreferences:
    return UserPreferences(
        id=uuid4(),
        user_id=user.id,
        min_savings_threshold=10.0,
        notify_price_drop=True,
        notify_delivery_anomaly=True,
        push_notifications_enabled=False,
        preferred_message_tone=MessageTone.polite,
        monitored_retailers=[],
        updated_at=datetime.now(timezone.utc),
    )


def _make_client(session: FakePrefsSession, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: (yield session)
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/users/me/preferences
# ---------------------------------------------------------------------------

def test_get_preferences_returns_existing():
    user = _make_user()
    prefs = _make_prefs(user)
    session = FakePrefsSession(user=user, prefs=prefs)
    client = _make_client(session, user)

    resp = client.get("/api/users/me/preferences")

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(user.id)
    assert data["min_savings_threshold"] == 10.0
    assert data["notify_price_drop"] is True
    assert data["preferred_message_tone"] == "polite"
    assert data["monitored_retailers"] == []


def test_get_preferences_creates_defaults_on_first_access():
    user = _make_user()
    session = FakePrefsSession(user=user, prefs=None)
    client = _make_client(session, user)

    resp = client.get("/api/users/me/preferences")

    assert resp.status_code == 200
    assert session.committed is True
    assert len(session.added) == 1
    assert isinstance(session.added[0], UserPreferences)
    assert session.added[0].user_id == user.id


# ---------------------------------------------------------------------------
# PATCH /api/users/me/preferences
# ---------------------------------------------------------------------------

def test_patch_updates_provided_fields():
    user = _make_user()
    prefs = _make_prefs(user)
    session = FakePrefsSession(user=user, prefs=prefs)
    client = _make_client(session, user)

    resp = client.patch("/api/users/me/preferences", json={
        "min_savings_threshold": 25.0,
        "notify_price_drop": False,
    })

    assert resp.status_code == 200
    assert prefs.min_savings_threshold == 25.0
    assert prefs.notify_price_drop is False
    assert session.committed is True


def test_patch_does_not_touch_omitted_fields():
    user = _make_user()
    prefs = _make_prefs(user)
    session = FakePrefsSession(user=user, prefs=prefs)
    client = _make_client(session, user)

    resp = client.patch("/api/users/me/preferences", json={
        "push_notifications_enabled": True,
    })

    assert resp.status_code == 200
    # Fields not in the body must be unchanged
    assert prefs.notify_price_drop is True
    assert prefs.notify_delivery_anomaly is True
    assert prefs.min_savings_threshold == 10.0


def test_patch_message_tone():
    user = _make_user()
    prefs = _make_prefs(user)
    session = FakePrefsSession(user=user, prefs=prefs)
    client = _make_client(session, user)

    resp = client.patch("/api/users/me/preferences", json={
        "preferred_message_tone": "firm",
    })

    assert resp.status_code == 200
    assert prefs.preferred_message_tone == MessageTone.firm


def test_patch_monitored_retailers():
    user = _make_user()
    prefs = _make_prefs(user)
    session = FakePrefsSession(user=user, prefs=prefs)
    client = _make_client(session, user)

    resp = client.patch("/api/users/me/preferences", json={
        "monitored_retailers": ["amazon", "target"],
    })

    assert resp.status_code == 200
    assert prefs.monitored_retailers == ["amazon", "target"]


def test_patch_creates_defaults_if_no_prefs_exist():
    user = _make_user()
    session = FakePrefsSession(user=user, prefs=None)
    client = _make_client(session, user)

    resp = client.patch("/api/users/me/preferences", json={
        "notify_price_drop": False,
    })

    assert resp.status_code == 200
    assert session.committed is True


def test_patch_empty_body_is_valid_noop():
    user = _make_user()
    prefs = _make_prefs(user)
    original_threshold = prefs.min_savings_threshold
    session = FakePrefsSession(user=user, prefs=prefs)
    client = _make_client(session, user)

    resp = client.patch("/api/users/me/preferences", json={})

    assert resp.status_code == 200
    assert prefs.min_savings_threshold == original_threshold
