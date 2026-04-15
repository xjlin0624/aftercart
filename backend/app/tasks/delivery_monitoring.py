import logging
from datetime import date, datetime
from typing import Any, Callable
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import session_scope
from ..models import (
    Alert, AlertPriority, AlertStatus, AlertType,
    DeliveryEvent, Order, UserPreferences,
)
from ..models.enums import DeliveryEventType, OrderStatus
from ..scrapers import DeliveryCheckResult, RetailerCircuitOpenError, RetailerNotReadyError, RetailerRateLimitedError, RetailerScrapeError, get_delivery_adapter


logger = logging.getLogger(__name__)

STALL_THRESHOLD_DAYS = 3

_TERMINAL_STATUSES = {OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.returned}


def detect_eta_slippage(
    order: Order,
    last_eta: date | None,
) -> DeliveryEvent | None:
    """
    Detect a change in estimated delivery date.

    Returns a DeliveryEvent(eta_updated) if the ETA changed relative to the
    last recorded baseline, with is_anomaly=True when the date slipped forward
    (later delivery), is_anomaly=False when it improved (earlier delivery).
    Returns None if the order is terminal, has no current ETA, or has no baseline.
    """
    if order.order_status in _TERMINAL_STATUSES:
        return None
    if order.estimated_delivery is None or last_eta is None:
        return None
    if order.estimated_delivery == last_eta:
        return None

    return DeliveryEvent(
        order_id=order.id,
        event_type=DeliveryEventType.eta_updated,
        previous_eta=last_eta,
        new_eta=order.estimated_delivery,
        is_anomaly=order.estimated_delivery > last_eta,
        notes=(
            f"ETA {'slipped' if order.estimated_delivery > last_eta else 'improved'} "
            f"from {last_eta.isoformat()} to {order.estimated_delivery.isoformat()}."
        ),
    )


def detect_stalled_tracking(
    order: Order,
    last_event_scraped_at: datetime | None,
    last_event_type: DeliveryEventType | None,
    today: date,
    stall_threshold_days: int = STALL_THRESHOLD_DAYS,
) -> DeliveryEvent | None:
    """
    Detect a stalled tracking feed for an in-transit order.

    Returns a DeliveryEvent(tracking_stalled, is_anomaly=True) if no new
    tracking event has been recorded in the last stall_threshold_days days.
    Returns None if the order is not in_transit, lacks a tracking number,
    has no baseline event, or was already flagged as stalled.
    """
    if order.order_status != OrderStatus.in_transit:
        return None
    if not order.tracking_number:
        return None
    if last_event_scraped_at is None:
        return None
    if last_event_type == DeliveryEventType.tracking_stalled:
        return None

    days_since = (today - last_event_scraped_at.date()).days
    if days_since < stall_threshold_days:
        return None

    return DeliveryEvent(
        order_id=order.id,
        event_type=DeliveryEventType.tracking_stalled,
        is_anomaly=True,
        notes=(
            f"No tracking update in {days_since} day(s) "
            f"(threshold: {stall_threshold_days} day(s))."
        ),
    )


def build_delivery_anomaly_alert(order: Order, event: DeliveryEvent) -> Alert:
    """
    Construct an Alert for a delivery anomaly event.

    Only called when event.is_anomaly is True.
    """
    if event.event_type == DeliveryEventType.eta_updated:
        slip_days = (event.new_eta - event.previous_eta).days
        title = f"Delivery date changed for order {order.retailer_order_id}"
        body = (
            f"Your estimated delivery date slipped by {slip_days} day(s) "
            f"from {event.previous_eta.isoformat()} to {event.new_eta.isoformat()}."
        )
    else:  # tracking_stalled
        title = f"Tracking stalled for order {order.retailer_order_id}"
        body = event.notes or "No tracking updates have been recorded recently."

    return Alert(
        user_id=order.user_id,
        order_id=order.id,
        alert_type=AlertType.delivery_anomaly,
        status=AlertStatus.new,
        priority=AlertPriority.medium,
        title=title,
        body=body,
        evidence={
            "event_type": event.event_type.value,
            "is_anomaly": event.is_anomaly,
            "previous_eta": event.previous_eta.isoformat() if event.previous_eta else None,
            "new_eta": event.new_eta.isoformat() if event.new_eta else None,
            "notes": event.notes,
        },
    )


def apply_delivery_check_result(order: Order, result: DeliveryCheckResult) -> list[DeliveryEvent]:
    events: list[DeliveryEvent] = []
    previous_status = order.order_status
    previous_eta = order.estimated_delivery

    if result.tracking_number:
        order.tracking_number = result.tracking_number
    if result.carrier:
        order.carrier = result.carrier
    if result.estimated_delivery:
        order.estimated_delivery = result.estimated_delivery
    if result.delivered_at:
        order.delivered_at = result.delivered_at
    if result.order_status:
        order.order_status = result.order_status

    if result.order_status and result.order_status != previous_status:
        event_type = (
            DeliveryEventType.delivered
            if result.order_status == OrderStatus.delivered
            else DeliveryEventType.status_changed
        )
        events.append(
            DeliveryEvent(
                order_id=order.id,
                event_type=event_type,
                previous_eta=previous_eta,
                new_eta=order.estimated_delivery,
                carrier_status_raw=result.carrier_status_raw,
                is_anomaly=False,
                notes=(
                    f"Delivery status changed from {previous_status.value} "
                    f"to {result.order_status.value}."
                ),
            )
        )

    return events


def _default_last_eta_lookup(session: Session, order_id: UUID) -> date | None:
    """Return the new_eta from the most recent eta_updated event for this order."""
    row = session.execute(
        select(DeliveryEvent.new_eta)
        .where(DeliveryEvent.order_id == order_id)
        .where(DeliveryEvent.event_type == DeliveryEventType.eta_updated)
        .order_by(DeliveryEvent.scraped_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return row


_CARRIER_EVENT_TYPES = {DeliveryEventType.status_changed, DeliveryEventType.delivered}


def _default_last_event_lookup(
    session: Session,
    order_id: UUID,
) -> tuple[datetime | None, DeliveryEventType | None]:
    """Return (carrier_scraped_at, last_any_event_type) for an order.

    carrier_scraped_at — scraped_at of the most recent carrier event
        (status_changed or delivered only). Used to measure staleness.
        System-generated events are excluded so they cannot reset the stall timer.

    last_any_event_type — event_type of the most recent event of any kind.
        Used for deduplication: if the last event was tracking_stalled, skip.
    """
    carrier_scraped_at = session.execute(
        select(DeliveryEvent.scraped_at)
        .where(DeliveryEvent.order_id == order_id)
        .where(DeliveryEvent.event_type.in_(_CARRIER_EVENT_TYPES))
        .order_by(DeliveryEvent.scraped_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    last_event_type = session.execute(
        select(DeliveryEvent.event_type)
        .where(DeliveryEvent.order_id == order_id)
        .order_by(DeliveryEvent.scraped_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    return carrier_scraped_at, last_event_type


def _default_existing_delivery_alert_lookup(session: Session, order_id: UUID) -> Alert | None:
    """Return an unresolved delivery_anomaly alert for this order, or None."""
    active_statuses = (AlertStatus.new, AlertStatus.viewed)
    return session.execute(
        select(Alert)
        .where(Alert.order_id == order_id)
        .where(Alert.alert_type == AlertType.delivery_anomaly)
        .where(Alert.status.in_(active_statuses))
        .limit(1)
    ).scalar_one_or_none()


def process_order_delivery_check(
    session: Session,
    order_id: str | UUID,
    prefs_lookup: Callable | None = None,
    last_eta_lookup: Callable = _default_last_eta_lookup,
    last_event_lookup: Callable = _default_last_event_lookup,
    existing_alert_lookup: Callable = _default_existing_delivery_alert_lookup,
    delivery_adapter_lookup: Callable = get_delivery_adapter,
    stall_threshold_days: int = STALL_THRESHOLD_DAYS,
) -> dict[str, Any]:
    order = session.get(Order, UUID(str(order_id)))
    if order is None:
        return {"status": "skipped_missing_order", "order_id": str(order_id), "events_created": 0, "alert_created": False}

    if order.order_status in _TERMINAL_STATUSES:
        return {"status": "skipped_terminal_order", "order_id": str(order_id), "events_created": 0, "alert_created": False}

    tracking_number = order.tracking_number if isinstance(order.tracking_number, str) else None
    order_url = order.order_url if isinstance(getattr(order, "order_url", None), str) else None
    if not tracking_number and not order_url:
        return {"status": "skipped_no_tracking", "order_id": str(order_id), "events_created": 0, "alert_created": False}

    if prefs_lookup is None:
        def prefs_lookup(uid):
            return session.execute(
                select(UserPreferences).where(UserPreferences.user_id == uid)
            ).scalar_one_or_none()

    prefs = prefs_lookup(order.user_id)
    notify = prefs.notify_delivery_anomaly if prefs else True

    today = date.today()
    last_eta = last_eta_lookup(session, order.id)
    last_scraped_at, last_event_type = last_event_lookup(session, order.id)

    existing_alert = existing_alert_lookup(session, order.id) if notify else None

    events_created = 0
    alert_created = False
    alert_skipped_duplicate = False
    scraped_delivery_applied = False

    retailer = order.retailer if isinstance(order.retailer, str) else None
    adapter = delivery_adapter_lookup(retailer)
    if adapter is not None and order_url:
        try:
            delivery_result = adapter.fetch_delivery_status(order)
        except (RetailerCircuitOpenError, RetailerRateLimitedError, RetailerNotReadyError, RetailerScrapeError) as exc:
            logger.warning(
                "Delivery check skipped for retailer=%s order_id=%s status=%s detail=%s",
                retailer,
                order.id,
                exc.status,
                exc,
            )
            return {
                "status": exc.status,
                "order_id": str(order.id),
                "retailer": retailer,
                "events_created": 0,
                "alert_created": False,
                "detail": str(exc),
            }
        except NotImplementedError:
            delivery_result = None
        else:
            if delivery_result is not None:
                scraped_delivery_applied = True
                for event in apply_delivery_check_result(order, delivery_result):
                    session.add(event)
                    events_created += 1

    eta_event = detect_eta_slippage(order, last_eta)
    if eta_event is not None:
        session.add(eta_event)
        events_created += 1
        if eta_event.is_anomaly and notify:
            if existing_alert is not None:
                alert_skipped_duplicate = True
            else:
                session.add(build_delivery_anomaly_alert(order, eta_event))
                alert_created = True

    stall_event = detect_stalled_tracking(order, last_scraped_at, last_event_type, today, stall_threshold_days)
    if stall_event is not None:
        session.add(stall_event)
        events_created += 1
        if notify and not alert_created:
            if existing_alert is not None:
                alert_skipped_duplicate = True
            else:
                session.add(build_delivery_anomaly_alert(order, stall_event))
                alert_created = True

    if events_created > 0 or scraped_delivery_applied:
        session.commit()

    return {
        "status": "checked" if events_created > 0 or scraped_delivery_applied else "checked_no_changes",
        "order_id": str(order_id),
        "events_created": events_created,
        "alert_created": alert_created,
        "alert_skipped_duplicate": alert_skipped_duplicate,
    }


def enqueue_candidate_delivery_checks(
    orders: list[Order],
    delay_fn: Callable,
) -> list[str]:
    """
    Enqueue delivery check tasks for trackable, non-terminal orders.

    Returns the list of order IDs that were enqueued.
    """
    selected_ids: list[str] = []
    for order in orders:
        if order.order_status in _TERMINAL_STATUSES:
            continue
        tracking_number = order.tracking_number if isinstance(order.tracking_number, str) else None
        order_url = order.order_url if isinstance(getattr(order, "order_url", None), str) else None
        if not tracking_number and not order_url:
            continue
        order_id = str(order.id)
        selected_ids.append(order_id)
        delay_fn(order_id)
    return selected_ids


@shared_task(name="delivery_check_cycle")
def delivery_check_cycle() -> dict[str, Any]:
    with session_scope() as session:
        orders = list(session.execute(select(Order)).scalars().all())
        selected_ids = enqueue_candidate_delivery_checks(
            orders=orders,
            delay_fn=check_order_delivery.delay,
        )
    logger.info("Enqueued %s delivery check tasks.", len(selected_ids))
    return {"status": "enqueued", "count": len(selected_ids), "order_ids": selected_ids}


@shared_task(name="check_order_delivery")
def check_order_delivery(order_id: str) -> dict[str, Any]:
    with session_scope() as session:
        result = process_order_delivery_check(session=session, order_id=order_id)
    logger.info(
        "Processed delivery check for order %s with status=%s.",
        order_id,
        result["status"],
    )
    return result
