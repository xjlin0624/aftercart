from datetime import date
from uuid import uuid4

from backend.app.models import DetectionMethod, Subscription, SubscriptionStatus
from backend.app.tasks.subscriptions import apply_cancellation_guidance, process_subscription_refresh

from .conftest import FakeSession


def _subscription(**overrides):
    data = {
        "id": uuid4(),
        "user_id": uuid4(),
        "retailer": "nike",
        "product_name": "Nike Membership",
        "detection_method": DetectionMethod.order_pattern,
        "status": SubscriptionStatus.monitoring,
        "last_charged_at": date(2026, 4, 1),
        "recurrence_interval_days": 30,
    }
    data.update(overrides)
    return Subscription(**data)


def test_apply_cancellation_guidance_updates_subscription():
    subscription = _subscription(retailer="sephora")

    applied = apply_cancellation_guidance(subscription)

    assert applied is True
    assert "sephora.com" in subscription.cancellation_url
    assert "1." in subscription.cancellation_steps


def test_process_subscription_refresh_updates_next_expected_charge_and_guidance():
    subscription = _subscription()
    session = FakeSession(subscription)

    result = process_subscription_refresh(session, subscription.id)

    assert result["status"] == "subscription_refreshed"
    assert result["guidance_applied"] is True
    assert subscription.next_expected_charge.isoformat() == "2026-05-01"
    assert session.committed is True


def test_process_subscription_refresh_guidance_only_when_schedule_missing():
    subscription = _subscription(last_charged_at=None, recurrence_interval_days=None)
    session = FakeSession(subscription)

    result = process_subscription_refresh(session, subscription.id)

    assert result["status"] == "subscription_guidance_refreshed"
    assert result["guidance_applied"] is True
    assert session.committed is True
