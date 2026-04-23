"""
Auth endpoint tests using FastAPI TestClient with a fake DB session.
No real database is required — consistent with the project's FakeSession pattern.
"""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.api.deps import get_db
from backend.app.core.security import create_refresh_token, hash_password, hash_token, verify_token
from backend.app.main import app
from backend.app.models.user import User


# ---------------------------------------------------------------------------
# Fake session infrastructure
# ---------------------------------------------------------------------------

class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *_args):
        return self

    def first(self):
        return self._result


class FakeAuthSession:
    def __init__(self, user=None):
        self._user = user
        self.added = []
        self.committed = False

    def query(self, _model):
        return _FakeQuery(self._user)

    def get(self, _model, pk):
        if self._user and str(self._user.id) == str(pk):
            return self._user
        return None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        # Simulate what SQLAlchemy/DB would populate after INSERT
        now = datetime.now(timezone.utc)
        if not obj.id:
            obj.id = uuid4()
        if obj.created_at is None:
            obj.created_at = now
        if obj.updated_at is None:
            obj.updated_at = now
        if obj.is_active is None:
            obj.is_active = True
        if obj.is_verified is None:
            obj.is_verified = False


def _override(session):
    """Return a FastAPI dependency override that yields the given session."""
    def _dep():
        yield session
    return _dep


def _make_client(session):
    app.dependency_overrides[get_db] = _override(session)
    client = TestClient(app)
    return client


def _active_user(password="password123") -> User:
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash=hash_password(password),
        is_active=True,
        is_verified=False,
    )
    return user


# ---------------------------------------------------------------------------
# /signup
# ---------------------------------------------------------------------------

def test_signup_creates_user_and_returns_201():
    session = FakeAuthSession(user=None)  # no existing user
    client = _make_client(session)

    resp = client.post("/api/auth/signup", json={
        "email": "new@example.com",
        "password": "Strongpass1",
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert "id" in data
    assert session.committed is True
    assert len(session.added) == 1


def test_signup_returns_409_when_email_taken():
    existing = _active_user()
    session = FakeAuthSession(user=existing)
    client = _make_client(session)

    resp = client.post("/api/auth/signup", json={
        "email": existing.email,
        "password": "Whatever1",
    })

    assert resp.status_code == 409


def test_signup_with_display_name():
    session = FakeAuthSession(user=None)
    client = _make_client(session)

    resp = client.post("/api/auth/signup", json={
        "email": "named@example.com",
        "password": "Password1",
        "display_name": "Alice",
    })

    assert resp.status_code == 201
    assert resp.json()["display_name"] == "Alice"


# ---------------------------------------------------------------------------
# /login
# ---------------------------------------------------------------------------

def test_login_returns_token_pair():
    user = _active_user(password="hunter2")
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/login", json={
        "email": user.email,
        "password": "hunter2",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_includes_user_in_response():
    user = _active_user(password="hunter2")
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})

    data = resp.json()
    assert "user" in data
    assert data["user"]["email"] == user.email
    assert "id" in data["user"]


def test_login_stores_hashed_refresh_token():
    user = _active_user(password="hunter2")
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})

    returned_refresh = resp.json()["refresh_token"]
    assert user.refresh_token_hash == hash_token(returned_refresh)
    assert session.committed is True


def test_login_wrong_password_returns_401():
    user = _active_user(password="correct")
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/login", json={
        "email": user.email,
        "password": "wrong",
    })

    assert resp.status_code == 401


def test_login_unknown_email_returns_401():
    session = FakeAuthSession(user=None)
    client = _make_client(session)

    resp = client.post("/api/auth/login", json={
        "email": "ghost@example.com",
        "password": "anything",
    })

    assert resp.status_code == 401


def test_login_inactive_user_returns_403():
    user = _active_user()
    user.is_active = False
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/login", json={
        "email": user.email,
        "password": "password123",
    })

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# /logout
# ---------------------------------------------------------------------------

def test_logout_clears_refresh_token_hash():
    user = _active_user()
    refresh_token = create_refresh_token(str(user.id))
    user.refresh_token_hash = hash_token(refresh_token)
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/logout", json={"refresh_token": refresh_token})

    assert resp.status_code == 204
    assert user.refresh_token_hash is None
    assert session.committed is True


def test_logout_invalid_token_returns_401():
    session = FakeAuthSession(user=None)
    client = _make_client(session)

    resp = client.post("/api/auth/logout", json={"refresh_token": "bad.token.here"})

    assert resp.status_code == 401


def test_logout_with_access_token_returns_401():
    from backend.app.core.security import create_access_token
    user = _active_user()
    access_token = create_access_token(str(user.id))
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/logout", json={"refresh_token": access_token})

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /refresh
# ---------------------------------------------------------------------------

def test_refresh_returns_new_token_pair():
    user = _active_user()
    refresh_token = create_refresh_token(str(user.id))
    user.refresh_token_hash = hash_token(refresh_token)
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_includes_user_in_response():
    user = _active_user()
    refresh_token = create_refresh_token(str(user.id))
    user.refresh_token_hash = hash_token(refresh_token)
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    data = resp.json()
    assert "user" in data
    assert data["user"]["email"] == user.email


def test_refresh_rotates_token():
    """The stored hash must verify the new token, not the old one."""
    user = _active_user()
    old_refresh = create_refresh_token(str(user.id))
    user.refresh_token_hash = hash_token(old_refresh)
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})

    new_refresh = resp.json()["refresh_token"]
    assert new_refresh != old_refresh  # jti claim makes every token unique
    assert verify_token(new_refresh, user.refresh_token_hash)
    assert not verify_token(old_refresh, user.refresh_token_hash)


def test_refresh_invalid_token_returns_401():
    session = FakeAuthSession(user=None)
    client = _make_client(session)

    resp = client.post("/api/auth/refresh", json={"refresh_token": "garbage"})

    assert resp.status_code == 401


def test_refresh_reuse_after_rotation_returns_401():
    """Using the old token after rotation must fail (token reuse attack)."""
    user = _active_user()
    old_refresh = create_refresh_token(str(user.id))
    user.refresh_token_hash = hash_token(old_refresh)
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    # First refresh — succeeds and rotates
    client.post("/api/auth/refresh", json={"refresh_token": old_refresh})

    # Second call with the same old token — hash no longer matches
    resp = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401


def test_refresh_with_access_token_returns_401():
    from backend.app.core.security import create_access_token
    user = _active_user()
    access_token = create_access_token(str(user.id))
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/refresh", json={"refresh_token": access_token})

    assert resp.status_code == 401


def test_refresh_no_stored_hash_returns_401():
    """User exists but has no refresh token stored (e.g. after logout)."""
    user = _active_user()
    user.refresh_token_hash = None
    refresh_token = create_refresh_token(str(user.id))
    session = FakeAuthSession(user=user)
    client = _make_client(session)

    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/users/me
# ---------------------------------------------------------------------------

def test_get_me_returns_current_user():
    from backend.app.core.security import create_access_token
    user = _active_user()
    now = datetime.now(timezone.utc)
    user.created_at = now
    user.updated_at = now
    session = FakeAuthSession(user=user)
    client = _make_client(session)
    token = create_access_token(str(user.id))

    resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == user.email
    assert data["id"] == str(user.id)


def test_get_me_returns_401_without_token():
    session = FakeAuthSession(user=None)
    client = _make_client(session)

    resp = client.get("/api/users/me")

    assert resp.status_code == 403
