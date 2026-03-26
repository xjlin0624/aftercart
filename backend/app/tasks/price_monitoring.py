import logging
from datetime import date
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..core import get_settings
from ..db import session_scope
from ..models import (
    Alert, AlertPriority, AlertStatus, AlertType,
    EffortLevel, OrderItem, PriceSnapshot, RecommendedAction, SnapshotSource,
    UserPreferences,
)
from ..scrapers import PriceCheckResult, get_price_adapter


logger = logging.getLogger(__name__)


def enqueue_candidate_price_checks(
    order_items: list[OrderItem],
    batch_size: int,
    delay_fn,
) -> list[str]:
    selected_ids: list[str] = []
    for order_item in order_items:
        if not order_item.is_monitoring_active or not order_item.product_url:
            continue
        selected_id = str(order_item.id)
        selected_ids.append(selected_id)
        delay_fn(selected_id)
        if len(selected_ids) >= batch_size:
            break
    return selected_ids


def should_create_price_drop_alert(
    paid_price: float,
    scraped_price: float,
    threshold: float,
    notify_price_drop: bool,
) -> bool:
    """Return True when a price drop meets the user's notification threshold."""
    if not notify_price_drop:
        return False
    return (paid_price - scraped_price) >= threshold


def build_price_drop_alert(
    order_item: OrderItem,
    snapshot: PriceSnapshot,
    threshold: float,
) -> Alert:
    """
    Construct an Alert for a detected price drop.

    Priority:
      high   — delta >= 2x threshold (significant saving)
      medium — delta >= threshold

    Recommended action:
      price_match      — retailer supports post-purchase price matching
      return_and_rebuy — return window still open
      no_action        — no actionable path available
    """
    delta = round(order_item.paid_price - snapshot.scraped_price, 2)
    order = order_item.order
    today = date.today()

    priority = AlertPriority.high if delta >= 2 * threshold else AlertPriority.medium

    if order and order.price_match_eligible:
        recommended_action = RecommendedAction.price_match
        effort = EffortLevel.low
        effort_steps = 3
    elif order and order.return_deadline and order.return_deadline >= today:
        recommended_action = RecommendedAction.return_and_rebuy
        effort = EffortLevel.medium
        effort_steps = 7
    else:
        recommended_action = RecommendedAction.no_action
        effort = EffortLevel.low
        effort_steps = 0

    days_remaining = None
    action_deadline = None
    if order and order.return_deadline:
        days_remaining = (order.return_deadline - today).days
        action_deadline = order.return_deadline

    return Alert(
        user_id=order_item.user_id,
        order_id=order_item.order_id,
        order_item_id=order_item.id,
        alert_type=AlertType.price_drop,
        status=AlertStatus.new,
        priority=priority,
        title=f"Price drop on {order_item.product_name}",
        body=(
            f"The price of {order_item.product_name} dropped from "
            f"${order_item.paid_price:.2f} to ${snapshot.scraped_price:.2f} "
            f"— you could save ${delta:.2f}."
        ),
        recommended_action=recommended_action,
        estimated_savings=delta,
        estimated_effort=effort,
        effort_steps_estimate=effort_steps,
        recommendation_rationale=(
            f"Current price ${snapshot.scraped_price:.2f} is ${delta:.2f} "
            f"below your purchase price of ${order_item.paid_price:.2f}."
        ),
        days_remaining_return=days_remaining,
        action_deadline=action_deadline,
        evidence={
            "price_at_purchase": order_item.paid_price,
            "price_now": snapshot.scraped_price,
            "product_url": order_item.product_url,
            "price_snapshot_ids": [str(snapshot.id)],
        },
    )


def process_order_item_price_check(
    session: Session,
    order_item_id: str | UUID,
    adapter_lookup=get_price_adapter,
    prefs_lookup=None,
) -> dict[str, Any]:
    stmt = (
        select(OrderItem)
        .options(selectinload(OrderItem.order))
        .where(OrderItem.id == UUID(str(order_item_id)))
    )
    order_item = session.execute(stmt).scalar_one_or_none()
    if order_item is None:
        return {"status": "skipped_missing_order_item", "order_item_id": str(order_item_id)}

    retailer = order_item.order.retailer if order_item.order else None
    adapter = adapter_lookup(retailer)
    if adapter is None:
        return {
            "status": "skipped_unsupported_retailer",
            "order_item_id": str(order_item.id),
            "retailer": retailer,
        }

    try:
        result: PriceCheckResult = adapter.fetch_current_price(order_item)
    except NotImplementedError:
        return {
            "status": "skipped_unsupported_retailer",
            "order_item_id": str(order_item.id),
            "retailer": retailer,
        }

    snapshot = PriceSnapshot(
        order_item_id=order_item.id,
        scraped_price=result.scraped_price,
        original_paid_price=order_item.paid_price,
        currency=result.currency,
        is_available=result.is_available,
        snapshot_source=SnapshotSource.scheduled_job,
    )
    session.add(snapshot)
    order_item.current_price = result.scraped_price

    # --- Price-drop detection (FR-7) ---
    if prefs_lookup is None:
        def prefs_lookup(uid):
            return session.execute(
                select(UserPreferences).where(UserPreferences.user_id == uid)
            ).scalar_one_or_none()

    prefs = prefs_lookup(order_item.user_id)
    threshold = prefs.min_savings_threshold if prefs else 10.0
    notify = prefs.notify_price_drop if prefs else True

    alert_created = False
    if should_create_price_drop_alert(
        paid_price=order_item.paid_price,
        scraped_price=result.scraped_price,
        threshold=threshold,
        notify_price_drop=notify,
    ):
        session.add(build_price_drop_alert(order_item, snapshot, threshold))
        alert_created = True

    session.commit()
    return {
        "status": "snapshot_created",
        "order_item_id": str(order_item.id),
        "retailer": retailer,
        "scraped_price": result.scraped_price,
        "alert_created": alert_created,
    }


@shared_task(name="price_check_cycle")
def price_check_cycle() -> dict[str, Any]:
    settings = get_settings()
    with session_scope() as session:
        stmt = select(OrderItem).options(selectinload(OrderItem.order)).order_by(OrderItem.created_at.asc())
        order_items = list(session.execute(stmt).scalars().all())
        selected_ids = enqueue_candidate_price_checks(
            order_items=order_items,
            batch_size=settings.price_check_batch_size,
            delay_fn=check_order_item_price.delay,
        )
    logger.info("Enqueued %s price check tasks.", len(selected_ids))
    return {"status": "enqueued", "count": len(selected_ids), "order_item_ids": selected_ids}


@shared_task(name="check_order_item_price")
def check_order_item_price(order_item_id: str) -> dict[str, Any]:
    with session_scope() as session:
        result = process_order_item_price_check(session=session, order_item_id=order_item_id)
    logger.info("Processed price check for order item %s with status=%s.", order_item_id, result["status"])
    return result
