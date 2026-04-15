import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import session_scope
from ..models import Subscription, SubscriptionStatus
from ..services.cancellation_guidance import get_cancellation_guidance


logger = logging.getLogger(__name__)
REFRESHABLE_STATUSES = {SubscriptionStatus.monitoring, SubscriptionStatus.active}


def enqueue_subscription_refreshes(
    subscriptions: list[Subscription],
    delay_fn,
) -> list[str]:
    selected_ids: list[str] = []
    for subscription in subscriptions:
        if subscription.status not in REFRESHABLE_STATUSES:
            continue
        selected_id = str(subscription.id)
        selected_ids.append(selected_id)
        delay_fn(selected_id)
    return selected_ids


def recalculate_next_expected_charge(subscription: Subscription):
    if subscription.last_charged_at is None or subscription.recurrence_interval_days is None:
        return None
    if subscription.recurrence_interval_days <= 0:
        return None
    return subscription.last_charged_at + timedelta(days=subscription.recurrence_interval_days)


def apply_cancellation_guidance(subscription: Subscription) -> bool:
    guidance = get_cancellation_guidance(subscription.retailer)
    if guidance is None:
        return False
    subscription.cancellation_url = guidance["cancellation_url"]
    subscription.cancellation_steps = "\n".join(
        f"{index + 1}. {step}" for index, step in enumerate(guidance["steps"])
    )
    return True


def process_subscription_refresh(session: Session, subscription_id: str | UUID) -> dict[str, Any]:
    stmt = select(Subscription).where(Subscription.id == UUID(str(subscription_id)))
    subscription = session.execute(stmt).scalar_one_or_none()
    if subscription is None:
        return {"status": "skipped_missing_subscription", "subscription_id": str(subscription_id)}
    if subscription.status not in REFRESHABLE_STATUSES:
        return {
            "status": "skipped_non_refreshable_status",
            "subscription_id": str(subscription.id),
            "current_status": subscription.status.value,
        }

    guidance_applied = apply_cancellation_guidance(subscription)
    next_expected_charge = recalculate_next_expected_charge(subscription)
    if next_expected_charge is None:
        if guidance_applied:
            session.commit()
        return {
            "status": "subscription_guidance_refreshed" if guidance_applied else "skipped_missing_schedule_data",
            "subscription_id": str(subscription.id),
            "guidance_applied": guidance_applied,
        }

    subscription.next_expected_charge = next_expected_charge
    session.commit()
    return {
        "status": "subscription_refreshed",
        "subscription_id": str(subscription.id),
        "next_expected_charge": subscription.next_expected_charge.isoformat(),
        "guidance_applied": guidance_applied,
    }


@shared_task(name="subscription_flag_refresh_cycle")
def subscription_flag_refresh_cycle() -> dict[str, Any]:
    with session_scope() as session:
        stmt = select(Subscription).order_by(Subscription.created_at.asc())
        subscriptions = list(session.execute(stmt).scalars().all())
        selected_ids = enqueue_subscription_refreshes(
            subscriptions=subscriptions,
            delay_fn=refresh_subscription_flag.delay,
        )
    logger.info("Enqueued %s subscription refresh tasks.", len(selected_ids))
    return {"status": "enqueued", "count": len(selected_ids), "subscription_ids": selected_ids}


@shared_task(name="refresh_subscription_flag")
def refresh_subscription_flag(subscription_id: str) -> dict[str, Any]:
    with session_scope() as session:
        result = process_subscription_refresh(session=session, subscription_id=subscription_id)
    logger.info(
        "Processed subscription refresh for subscription %s with status=%s.",
        subscription_id,
        result["status"],
    )
    return result
