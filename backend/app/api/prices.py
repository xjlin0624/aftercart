import logging
from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .deps import CurrentUser, DB
from ..models.alert import Alert
from ..models.enums import AlertStatus, SnapshotSource
from ..models.order_item import OrderItem
from ..models.price_snapshot import PriceSnapshot
from ..models.user_preferences import UserPreferences
from ..schemas.price_snapshot import PriceSnapshotRead
from ..tasks.price_monitoring import build_price_drop_alert, should_create_price_drop_alert

router = APIRouter(prefix="/prices", tags=["prices"])
logger = logging.getLogger(__name__)


class PriceCaptureIn(BaseModel):
    retailer: str
    product_id: str | None = None
    product_name: str | None = None
    product_url: str | None = None
    source_url: str | None = None
    scraped_price: float = Field(gt=0)
    currency: str = "USD"
    captured_at: datetime | None = None

    @field_validator("retailer", mode="before")
    @classmethod
    def normalize_retailer(cls, value: str) -> str:
        return value.strip().lower()


class PriceCaptureResult(BaseModel):
    status: str
    retailer: str
    matched_order_item_ids: list[UUID] = []
    snapshot_count: int = 0
    alert_created_count: int = 0
    duplicate_alert_count: int = 0


def _normalize_url_for_match(value: str | None) -> str | None:
    if not value:
        return None

    try:
        parsed = urlsplit(value)
    except ValueError:
        return value.strip().rstrip("/").lower() or None

    normalized_path = parsed.path.rstrip("/") or "/"
    return f"{parsed.netloc.lower()}{normalized_path.lower()}"


def _default_candidate_lookup(session, user_id) -> list[OrderItem]:
    stmt = (
        select(OrderItem)
        .options(selectinload(OrderItem.order))
        .where(OrderItem.user_id == user_id)
        .where(OrderItem.is_monitoring_active.is_(True))
    )
    return list(session.execute(stmt).scalars().all())


def _default_preferences_lookup(session, user_id) -> UserPreferences | None:
    return session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    ).scalar_one_or_none()


def _default_existing_alert_lookup(session, order_item_id) -> Alert | None:
    active_statuses = (AlertStatus.new, AlertStatus.viewed)
    return session.execute(
        select(Alert)
        .where(Alert.order_item_id == order_item_id)
        .where(Alert.status.in_(active_statuses))
        .limit(1)
    ).scalar_one_or_none()


def _matches_captured_price(order_item: OrderItem, body: PriceCaptureIn) -> bool:
    retailer = getattr(order_item.order, "retailer", None)
    if retailer != body.retailer:
        return False

    product_id = (body.product_id or "").strip().lower()
    item_sku = (order_item.sku or "").strip().lower()
    if product_id and item_sku and product_id == item_sku:
        return True

    target_urls = {
        _normalize_url_for_match(body.product_url),
        _normalize_url_for_match(body.source_url),
    }
    target_urls.discard(None)
    if target_urls:
        item_url = _normalize_url_for_match(order_item.product_url)
        if item_url and item_url in target_urls:
            return True

    product_name = (body.product_name or "").strip().lower()
    item_name = (order_item.product_name or "").strip().lower()
    return bool(product_name and item_name and product_name == item_name)


def process_extension_price_capture(
    session,
    current_user_id,
    body: PriceCaptureIn,
    candidate_lookup=None,
    preferences_lookup=None,
    existing_alert_lookup=_default_existing_alert_lookup,
) -> PriceCaptureResult:
    if candidate_lookup is None:
        candidate_lookup = _default_candidate_lookup
    if preferences_lookup is None:
        def preferences_lookup(user_id):
            return _default_preferences_lookup(session, user_id)

    matched_items = [
        item
        for item in candidate_lookup(session, current_user_id)
        if _matches_captured_price(item, body)
    ]

    if not matched_items:
        logger.info(
            "Extension price capture did not match any tracked item for retailer=%s product_id=%s source_url=%s.",
            body.retailer,
            body.product_id,
            body.source_url,
        )
        return PriceCaptureResult(status="skipped_no_matching_item", retailer=body.retailer)

    preferences = preferences_lookup(current_user_id)
    threshold = preferences.min_savings_threshold if preferences else 10.0
    notify_price_drop = preferences.notify_price_drop if preferences else True

    alert_created_count = 0
    duplicate_alert_count = 0

    for item in matched_items:
        snapshot = PriceSnapshot(
            order_item_id=item.id,
            scraped_price=body.scraped_price,
            original_paid_price=item.paid_price,
            currency=body.currency,
            snapshot_source=SnapshotSource.extension_capture,
        )
        session.add(snapshot)
        flush = getattr(session, "flush", None)
        if callable(flush):
            flush()

        item.current_price = body.scraped_price

        if should_create_price_drop_alert(
            paid_price=item.paid_price,
            scraped_price=body.scraped_price,
            threshold=threshold,
            notify_price_drop=notify_price_drop,
        ):
            if existing_alert_lookup(session, item.id) is not None:
                duplicate_alert_count += 1
            else:
                session.add(build_price_drop_alert(item, snapshot, threshold))
                alert_created_count += 1

    session.commit()

    return PriceCaptureResult(
        status="snapshot_created",
        retailer=body.retailer,
        matched_order_item_ids=[item.id for item in matched_items],
        snapshot_count=len(matched_items),
        alert_created_count=alert_created_count,
        duplicate_alert_count=duplicate_alert_count,
    )


@router.post("/captures", response_model=PriceCaptureResult)
def capture_extension_price(
    body: PriceCaptureIn,
    db: DB,
    current_user: CurrentUser,
) -> PriceCaptureResult:
    return process_extension_price_capture(
        session=db,
        current_user_id=current_user.id,
        body=body,
    )


@router.get("/{item_id}/history", response_model=list[PriceSnapshotRead])
def get_item_price_history(
    item_id: UUID,
    db: DB,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PriceSnapshot]:
    """
    Return price snapshots for an order item, newest first (FR-6).

    Verifies that the item belongs to the authenticated user before
    returning data.  Returns 404 if the item does not exist or is
    owned by another user.
    """
    item = db.get(OrderItem, item_id)
    if item is None or item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

    return (
        db.query(PriceSnapshot)
        .filter(PriceSnapshot.order_item_id == item_id)
        .order_by(PriceSnapshot.scraped_at.desc())
        .limit(limit)
        .all()
    )
