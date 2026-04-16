from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from .deps import CurrentUser, DB
from ..models.alert import Alert
from ..models.order import Order
from ..models.order_item import OrderItem
from ..models.enums import AlertPriority, AlertStatus, AlertType, MessageTone
from ..models.user_preferences import UserPreferences
from ..schemas.alert import (
    AlertCreate,
    AlertRead,
    AlertUpdate,
    ExplainedRecommendation,
    GeneratedMessage,
)
from ..services.gemini import generate_support_message, static_fallback_for_alert
from ..tasks.price_monitoring import build_explained_recommendation

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
def create_alert(
    body: AlertCreate,
    db: DB,
    current_user: CurrentUser,
) -> Alert:
    related_order = None
    if body.order_id is not None:
        related_order = db.get(Order, body.order_id)
        if related_order is None or related_order.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    related_item = None
    if body.order_item_id is not None:
        related_item = db.get(OrderItem, body.order_item_id)
        if related_item is None or related_item.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
        if related_order is not None and related_item.order_id != related_order.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order item does not belong to the selected order",
            )

    alert = Alert(
        user_id=current_user.id,
        order_id=related_order.id if related_order is not None else body.order_id,
        order_item_id=related_item.id if related_item is not None else body.order_item_id,
        alert_type=body.alert_type,
        priority=body.priority,
        status=AlertStatus.new,
        title=body.title,
        body=body.body,
        evidence=body.evidence,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("", response_model=list[AlertRead])
def list_alerts(
    db: DB,
    current_user: CurrentUser,
    alert_status: AlertStatus | None = Query(default=None, alias="status"),
    alert_type: AlertType | None = Query(default=None, alias="type"),
    priority: AlertPriority | None = Query(default=None),
    unread: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Alert]:
    """
    Return alerts for the authenticated user, newest first.

    Optionally filter by ?status=new|viewed|resolved|dismissed|expired.
    """
    stmt = select(Alert).where(Alert.user_id == current_user.id)
    if alert_status is not None:
        stmt = stmt.where(Alert.status == alert_status)
    if alert_type is not None:
        stmt = stmt.where(Alert.alert_type == alert_type)
    if priority is not None:
        stmt = stmt.where(Alert.priority == priority)
    if unread is True:
        stmt = stmt.where(Alert.status == AlertStatus.new)
    if unread is False:
        stmt = stmt.where(Alert.status != AlertStatus.new)
    stmt = stmt.order_by(Alert.created_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get("/{alert_id}", response_model=AlertRead)
def get_alert(
    alert_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> Alert:
    """
    Return a single alert by ID.
    Returns 404 if the alert does not exist or belongs to another user.
    """
    alert = db.get(Alert, alert_id)
    if alert is None or alert.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.get("/{alert_id}/recommendation", response_model=ExplainedRecommendation)
def get_alert_recommendation(
    alert_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> ExplainedRecommendation:
    """
    Return a structured, explainable recommendation payload for an alert.

    Includes the decision factors and action steps that explain why the
    recommendation was made and how the user can act on it.
    Returns 404 if the alert does not exist or belongs to another user.
    Returns 422 if the alert has no recommendation (e.g. non-price-drop alerts).
    """
    alert = db.get(Alert, alert_id)
    if alert is None or alert.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if alert.recommended_action is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This alert has no recommendation",
        )
    return build_explained_recommendation(alert)


@router.patch("/{alert_id}/resolve", response_model=AlertRead)
def resolve_alert(
    alert_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> Alert:
    """
    Mark an alert as resolved and record the resolution timestamp.
    Idempotent: resolved_at is only set on the first call.
    Returns 404 if the alert does not exist or belongs to another user.
    """
    alert = db.get(Alert, alert_id)
    if alert is None or alert.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.status = AlertStatus.resolved
    if alert.resolved_at is None:
        alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


@router.patch("/{alert_id}/dismiss", response_model=AlertRead)
def dismiss_alert(
    alert_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> Alert:
    """
    Mark an alert as dismissed and record the resolution timestamp.
    Idempotent: resolved_at is only set on the first call.
    Returns 404 if the alert does not exist or belongs to another user.
    """
    alert = db.get(Alert, alert_id)
    if alert is None or alert.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.status = AlertStatus.dismissed
    if alert.resolved_at is None:
        alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/{alert_id}/message", response_model=GeneratedMessage)
def get_support_message(
    alert_id: UUID,
    db: DB,
    current_user: CurrentUser,
    tone: MessageTone | None = Query(default=None),
) -> GeneratedMessage:
    """
    Generate a customer support message for an alert.

    Tone defaults to the user's preferred_message_tone from their preferences.
    Pass ?tone=polite|firm|concise to override.
    Repeated calls with the same tone are deduplicated by the Redis LLM cache
    (15-minute TTL) — no permanent DB-level caching so tone changes always
    produce a fresh generation.
    """
    alert = db.get(Alert, alert_id)
    if alert is None or alert.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    # Resolve tone: query param > user preference > default polite
    if tone is None:
        prefs = db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        ).scalar_one_or_none()
        tone = prefs.preferred_message_tone if prefs else MessageTone.polite

    tone_key = tone.value

    # Generate via Gemini (Redis handles short-term deduplication), fall back to static template on failure
    is_fallback = False
    try:
        message = generate_support_message(alert, tone)
    except RuntimeError:
        message = static_fallback_for_alert(alert)
        is_fallback = True

    return GeneratedMessage(
        alert_id=alert_id,
        tone=tone_key,
        message=message,
        cached=False,
        fallback=is_fallback,
    )


@router.patch("/{alert_id}", response_model=AlertRead)
def update_alert(
    alert_id: UUID,
    body: AlertUpdate,
    db: DB,
    current_user: CurrentUser,
) -> Alert:
    """
    Update an alert's status (e.g. mark as viewed, resolved, or dismissed).
    Returns 404 if the alert does not exist or belongs to another user.
    """
    alert = db.get(Alert, alert_id)
    if alert is None or alert.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)

    if body.status is not None and body.status in (AlertStatus.resolved, AlertStatus.dismissed) and alert.resolved_at is None:
        alert.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(alert)
    return alert
