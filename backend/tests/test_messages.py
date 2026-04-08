"""
Tests for POST /api/messages/generate endpoint and order-based prompt building.
Gemini API calls are mocked — no real API key needed.
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.enums import MessageTone, OrderStatus
from backend.app.models.order import Order
from backend.app.models.order_item import OrderItem
from backend.app.models.user import User
from backend.app.services.gemini import _build_order_prompt


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeOrderSession:
    def __init__(self, order=None):
        self._order = order

    def get(self, _model, pk):
        if self._order and str(self._order.id) == str(pk):
            return self._order
        return None


def _make_user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        password_hash="hash",
        is_active=True,
        is_verified=False,
    )


def _make_order(user_id, with_items=True, return_deadline=None):
    order_id = uuid4()
    order = Order(
        id=order_id,
        user_id=user_id,
        retailer="Nike",
        retailer_order_id="ORD-001",
        order_status=OrderStatus.delivered,
        order_date=__import__("datetime").datetime(2024, 1, 1, tzinfo=__import__("datetime").timezone.utc),
        subtotal=120.00,
        return_deadline=return_deadline,
    )
    if with_items:
        order.items = [
            OrderItem(
                id=uuid4(),
                order_id=order_id,
                user_id=user_id,
                product_name="Air Max 270",
                product_url="https://nike.com/airmax270",
                paid_price=120.00,
                current_price=95.00,
            )
        ]
    else:
        order.items = []
    return order


def _make_client(session, user) -> TestClient:
    app.dependency_overrides[get_db] = lambda: (yield session)
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


# ---------------------------------------------------------------------------
# _build_order_prompt tests
# ---------------------------------------------------------------------------

def test_build_order_prompt_price_match_includes_prices():
    user = _make_user()
    order = _make_order(user.id)
    prompt = _build_order_prompt(order, "price_match", MessageTone.polite)
    assert "120.00" in prompt
    assert "95.00" in prompt
    assert "25.00" in prompt  # savings


def test_build_order_prompt_price_match_includes_retailer():
    user = _make_user()
    order = _make_order(user.id)
    prompt = _build_order_prompt(order, "price_match", MessageTone.polite)
    assert "Nike" in prompt


def test_build_order_prompt_return_includes_deadline():
    user = _make_user()
    order = _make_order(user.id, return_deadline=date(2025, 4, 1))
    prompt = _build_order_prompt(order, "return_request", MessageTone.firm)
    assert "2025-04-01" in prompt
    assert "return" in prompt.lower()


def test_build_order_prompt_tone_differs():
    user = _make_user()
    order = _make_order(user.id)
    polite = _build_order_prompt(order, "price_match", MessageTone.polite)
    firm = _build_order_prompt(order, "price_match", MessageTone.firm)
    concise = _build_order_prompt(order, "price_match", MessageTone.concise)
    assert polite != firm
    assert firm != concise


def test_build_order_prompt_no_items_falls_back_gracefully():
    user = _make_user()
    order = _make_order(user.id, with_items=False)
    prompt = _build_order_prompt(order, "price_match", MessageTone.polite)
    assert "my order" in prompt


# ---------------------------------------------------------------------------
# POST /api/messages/generate endpoint tests
# ---------------------------------------------------------------------------

def test_generate_message_returns_200():
    user = _make_user()
    order = _make_order(user.id)
    session = FakeOrderSession(order=order)
    client = _make_client(session, user)

    with patch("backend.app.api.messages.generate_message_from_order", return_value="Please match the price."):
        resp = client.post("/api/messages/generate", json={
            "order_id": str(order.id),
            "request_type": "price_match",
            "tone": "polite",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Please match the price."
    assert data["tone"] == "polite"
    assert data["request_type"] == "price_match"


def test_generate_message_default_tone_is_polite():
    user = _make_user()
    order = _make_order(user.id)
    session = FakeOrderSession(order=order)
    client = _make_client(session, user)

    with patch("backend.app.api.messages.generate_message_from_order", return_value="Hi.") as mock_gen:
        client.post("/api/messages/generate", json={
            "order_id": str(order.id),
            "request_type": "price_match",
        })

    mock_gen.assert_called_once()
    _, _, tone_arg = mock_gen.call_args.args
    assert tone_arg == MessageTone.polite


def test_generate_message_return_request_type():
    user = _make_user()
    order = _make_order(user.id)
    session = FakeOrderSession(order=order)
    client = _make_client(session, user)

    with patch("backend.app.api.messages.generate_message_from_order", return_value="I want to return.") as mock_gen:
        resp = client.post("/api/messages/generate", json={
            "order_id": str(order.id),
            "request_type": "return_request",
            "tone": "firm",
        })

    assert resp.status_code == 200
    mock_gen.assert_called_once()
    _, req_type, _ = mock_gen.call_args.args
    assert req_type == "return_request"


def test_generate_message_invalid_request_type_returns_400():
    user = _make_user()
    order = _make_order(user.id)
    session = FakeOrderSession(order=order)
    client = _make_client(session, user)

    resp = client.post("/api/messages/generate", json={
        "order_id": str(order.id),
        "request_type": "refund",
        "tone": "polite",
    })

    assert resp.status_code == 400


def test_generate_message_order_not_found_returns_404():
    user = _make_user()
    session = FakeOrderSession(order=None)
    client = _make_client(session, user)

    resp = client.post("/api/messages/generate", json={
        "order_id": str(uuid4()),
        "request_type": "price_match",
    })

    assert resp.status_code == 404


def test_generate_message_other_users_order_returns_404():
    user = _make_user()
    other_order = _make_order(uuid4())  # belongs to a different user
    session = FakeOrderSession(order=other_order)
    client = _make_client(session, user)

    resp = client.post("/api/messages/generate", json={
        "order_id": str(other_order.id),
        "request_type": "price_match",
    })

    assert resp.status_code == 404


def test_generate_message_price_match_no_price_drop_returns_422():
    user = _make_user()
    order = _make_order(user.id)
    # Set current_price >= paid_price so no drop exists
    order.items[0].current_price = 120.00
    session = FakeOrderSession(order=order)
    client = _make_client(session, user)

    resp = client.post("/api/messages/generate", json={
        "order_id": str(order.id),
        "request_type": "price_match",
    })

    assert resp.status_code == 422


def test_generate_message_gemini_unavailable_returns_fallback():
    user = _make_user()
    order = _make_order(user.id)
    session = FakeOrderSession(order=order)
    client = _make_client(session, user)

    with patch("backend.app.api.messages.generate_message_from_order",
               side_effect=RuntimeError("GEMINI_API_KEY is not configured.")):
        resp = client.post("/api/messages/generate", json={
            "order_id": str(order.id),
            "request_type": "price_match",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["fallback"] is True
    assert len(data["message"]) > 0
