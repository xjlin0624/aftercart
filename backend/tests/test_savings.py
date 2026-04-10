"""
Tests for GET /api/savings/summary.
Uses TestClient + dependency_overrides, no real DB.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.enums import ActionTaken
from backend.app.models.outcome_log import OutcomeLog
from backend.app.models.user import User


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fake session
# ---------------------------------------------------------------------------

class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return self._value if isinstance(self._value, list) else [self._value]


class FakeSavingsSession:
    """
    Drives each successive db.execute() call from a queue so tests can
    supply exactly the sequence of results the handler expects.
    """
    def __init__(self, results):
        # results is a list of values returned by sequential execute() calls
        self._queue = list(results)

    def execute(self, _stmt):
        value = self._queue.pop(0)
        return _ScalarResult(value)


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


def _make_outcome(user_id, action=ActionTaken.price_matched, recovered=10.0, successful=True):
    return OutcomeLog(
        id=uuid4(),
        user_id=user_id,
        action_taken=action,
        recovered_value=recovered,
        was_successful=successful,
        logged_at=datetime.now(timezone.utc),
    )


# Fake row returned by the GROUP BY query
class _ByActionRow:
    def __init__(self, action_taken, count, total_recovered):
        self.action_taken = action_taken
        self.count = count
        self.total_recovered = total_recovered


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_summary_returns_correct_totals():
    user = _make_user()
    outcome = _make_outcome(user.id, recovered=25.0)
    by_action_row = _ByActionRow(ActionTaken.price_matched, 1, 25.0)

    # execute() is called 4 times: total_recovered, total_actions,
    # successful_actions, by_action groupby — then scalars() for history list
    db = FakeSavingsSession([
        25.0,           # total_recovered scalar
        1,              # total_actions scalar
        1,              # successful_actions scalar
        [by_action_row],  # by_action rows (.all())
        [outcome],      # history (.scalars().all())
    ])
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    resp = TestClient(app).get("/api/savings/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_recovered"] == 25.0
    assert data["total_actions"] == 1
    assert data["successful_actions"] == 1
    assert len(data["by_action"]) == 1
    assert data["by_action"][0]["action_taken"] == "price_matched"
    assert data["by_action"][0]["count"] == 1
    assert data["by_action"][0]["total_recovered"] == 25.0
    assert len(data["history"]) == 1


def test_total_recovered_only_counts_successful_actions():
    """total_recovered must not include pending or failed outcomes."""
    user = _make_user()
    # DB returns 30.0 for the successful-only sum (not the 80.0 total including failures)
    db = FakeSavingsSession([30.0, 3, 1, [], []])
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    resp = TestClient(app).get("/api/savings/summary")
    assert resp.status_code == 200
    assert resp.json()["total_recovered"] == 30.0


def test_summary_empty_returns_zeros():
    user = _make_user()
    db = FakeSavingsSession([0.0, 0, 0, [], []])
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    resp = TestClient(app).get("/api/savings/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_recovered"] == 0.0
    assert data["total_actions"] == 0
    assert data["successful_actions"] == 0
    assert data["by_action"] == []
    assert data["history"] == []


def test_summary_multiple_action_types():
    user = _make_user()
    rows = [
        _ByActionRow(ActionTaken.price_matched, 3, 45.0),
        _ByActionRow(ActionTaken.returned_and_rebought, 2, 80.0),
    ]
    history = [
        _make_outcome(user.id, ActionTaken.price_matched, 15.0),
        _make_outcome(user.id, ActionTaken.returned_and_rebought, 40.0),
    ]
    db = FakeSavingsSession([125.0, 5, 4, rows, history])
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    resp = TestClient(app).get("/api/savings/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_recovered"] == 125.0
    assert data["total_actions"] == 5
    assert data["successful_actions"] == 4
    assert len(data["by_action"]) == 2
    assert len(data["history"]) == 2


def test_summary_history_includes_required_fields():
    user = _make_user()
    outcome = _make_outcome(user.id, recovered=12.0, successful=True)
    db = FakeSavingsSession([12.0, 1, 1, [], [outcome]])
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    resp = TestClient(app).get("/api/savings/summary")
    assert resp.status_code == 200
    entry = resp.json()["history"][0]
    assert "id" in entry
    assert "action_taken" in entry
    assert "recovered_value" in entry
    assert "logged_at" in entry


def test_summary_limit_param_accepted():
    user = _make_user()
    db = FakeSavingsSession([0.0, 0, 0, [], []])
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    resp = TestClient(app).get("/api/savings/summary?limit=10")
    assert resp.status_code == 200


def test_summary_limit_out_of_range_returns_422():
    user = _make_user()
    db = FakeSavingsSession([])
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    resp = TestClient(app).get("/api/savings/summary?limit=0")
    assert resp.status_code == 422
