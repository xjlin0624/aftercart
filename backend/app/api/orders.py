import logging
from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import field_validator, model_validator
from sqlalchemy.orm import Session

from .deps import CurrentUser, DB
from ..models.enums import SnapshotSource
from ..models.order import Order
from ..models.order_item import OrderItem
from ..models.price_snapshot import PriceSnapshot
from ..schemas.order import OrderCreate, OrderRead
from ..schemas.order_item import OrderItemCreate, OrderItemRead

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger(__name__)

# Retailer price-match policy.  Keyed by the normalised retailer slug (lowercase,
# stripped).  Authoritative at order ingestion — overrides whatever the extension
# sends so the flag is always consistent with the retailer's actual policy.
_PRICE_MATCH_POLICY: dict[str, bool] = {
    "nike": True,       # Nike offers price adjustments within 14 days of purchase
    "sephora": True,    # Sephora offers price adjustments within 30 days of purchase
}


# ---------------------------------------------------------------------------
# Return-window deadline calculation
# ---------------------------------------------------------------------------

def compute_return_deadline(
    order_date,
    return_window_days: int | None,
    explicit_deadline: date | None,
) -> date | None:
    """
    Return the correct return_deadline for an order.

    Rules:
    - If an explicit deadline is already set, use it unchanged.
    - If return_window_days is provided, compute order_date.date() + window.
    - Otherwise return None.
    """
    if explicit_deadline is not None:
        return explicit_deadline
    if return_window_days is not None:
        # datetime is a subclass of date, so check datetime first
        order_dt = order_date.date() if isinstance(order_date, datetime) else order_date
        return order_dt + timedelta(days=return_window_days)
    return None


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class OrderIngest(OrderCreate):
    """OrderCreate extended with an optional list of line items."""
    items: list[OrderItemCreate] = []

    @field_validator("retailer", mode="before")
    @classmethod
    def normalize_retailer(cls, v: str) -> str:
        """Lowercase and strip so 'AMAZON ', 'Amazon', 'amazon' are all the same."""
        return v.strip().lower()

    @field_validator("retailer_order_id", mode="before")
    @classmethod
    def normalize_order_id(cls, v: str) -> str:
        """Strip surrounding whitespace to avoid whitespace-only duplicates."""
        return v.strip()

    @model_validator(mode="after")
    def fill_return_deadline(self) -> "OrderIngest":
        """
        Compute return_deadline from order_date + return_window_days when the
        caller supplies a window but no explicit deadline.  An explicit deadline
        in the request is always respected as-is.
        """
        self.return_deadline = compute_return_deadline(
            order_date=self.order_date,
            return_window_days=self.return_window_days,
            explicit_deadline=self.return_deadline,
        )
        return self


class OrderReadWithItems(OrderRead):
    items: list[OrderItemRead] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# De-duplication helper
# ---------------------------------------------------------------------------

def find_or_create_order(
    db: Session,
    user_id,
    retailer: str,
    retailer_order_id: str,
) -> tuple[Order, bool]:
    """
    Look up an existing order by the dedup key (user_id, retailer, retailer_order_id).
    Returns (order, is_new).  The caller is responsible for flush/commit.
    """
    order = (
        db.query(Order)
        .filter(
            Order.user_id == user_id,
            Order.retailer == retailer,
            Order.retailer_order_id == retailer_order_id,
        )
        .first()
    )
    if order is not None:
        return order, False

    order = Order(user_id=user_id)
    db.add(order)
    return order, True


# ---------------------------------------------------------------------------
# Price monitoring enrollment
# ---------------------------------------------------------------------------

def enroll_items_for_price_monitoring(
    items: list,
    enqueue_fn=None,
) -> int:
    """
    Dispatch check_order_item_price for each item eligible for monitoring.

    Eligibility mirrors the filter in enqueue_candidate_price_checks:
      - is_monitoring_active is True
      - product_url is set (required for scraping)

    enqueue_fn defaults to check_order_item_price.delay (lazy import so the
    Celery task module is only loaded when actually needed, keeping tests fast).
    Dispatch errors are logged and swallowed so a broker outage never fails
    the ingestion request.

    Returns the count of items successfully enqueued.
    """
    if enqueue_fn is None:
        from ..tasks.price_monitoring import check_order_item_price
        enqueue_fn = check_order_item_price.delay

    count = 0
    for item in items:
        if not item.is_monitoring_active or not item.product_url:
            continue
        try:
            enqueue_fn(str(item.id))
            count += 1
        except Exception:
            logger.warning("Failed to enqueue price check for item %s", item.id)
    return count


# ---------------------------------------------------------------------------
# Price snapshot storage
# ---------------------------------------------------------------------------

def record_extension_capture_snapshot(db: Session, item: OrderItem) -> PriceSnapshot:
    """
    Seed the price history for a newly ingested item.

    Records paid_price as the first observed price with source=extension_capture.
    This gives the time-series a baseline so price_delta is meaningful from day one,
    even before the first scraper run.

    item.id must already be assigned (call db.flush() before this).
    """
    snapshot = PriceSnapshot(
        order_item_id=item.id,
        scraped_price=item.paid_price,
        original_paid_price=item.paid_price,
        snapshot_source=SnapshotSource.extension_capture,
    )
    db.add(snapshot)
    return snapshot


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("", response_model=OrderReadWithItems)
def ingest_order(
    body: OrderIngest,
    db: DB,
    current_user: CurrentUser,
    response: Response,
) -> Order:
    """
    Create or update an order for the authenticated user (FR-4 de-duplication).

    Dedup key: (user_id, retailer, retailer_order_id).  Both `retailer` and
    `retailer_order_id` are normalised before the lookup so that minor
    formatting differences in the extension output don't produce duplicate rows.

    Returns 201 on first capture, 200 on subsequent re-captures of the same order.
    Items are fully replaced on each call so the stored state always mirrors the
    latest extension snapshot.
    """
    order, is_new = find_or_create_order(
        db,
        user_id=current_user.id,
        retailer=body.retailer,
        retailer_order_id=body.retailer_order_id,
    )

    # Apply scalar fields (normalization already done by Pydantic validators)
    for field, value in body.model_dump(exclude={"items"}).items():
        setattr(order, field, value)

    # Override price_match_eligible from the server-side policy so it is always
    # accurate regardless of what the extension sends.
    order.price_match_eligible = _PRICE_MATCH_POLICY.get(body.retailer, False)

    db.flush()  # ensure order.id is assigned before inserting items

    # Replace items — delete-then-insert keeps the stored set in sync with the
    # extension's latest capture without needing per-item identity tracking.
    db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
    new_items: list[OrderItem] = []
    for item_data in body.items:
        item = OrderItem(
            order_id=order.id,
            user_id=current_user.id,
            **item_data.model_dump(),
        )
        db.add(item)
        new_items.append(item)

    db.flush()  # assign item IDs before creating snapshot FKs

    # Seed the price time-series with the purchase price for each new item.
    for item in new_items:
        record_extension_capture_snapshot(db, item)

    db.commit()
    db.refresh(order)

    enroll_items_for_price_monitoring(order.items)

    response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
    return order


@router.get("", response_model=list[OrderReadWithItems])
def list_orders(
    db: DB,
    current_user: CurrentUser,
    retailer: str | None = Query(default=None, description="Filter by retailer slug"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by order status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Order]:
    """List all orders for the authenticated user, newest first."""
    q = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
    )
    if retailer is not None:
        q = q.filter(Order.retailer == retailer.strip().lower())
    if status_filter is not None:
        q = q.filter(Order.order_status == status_filter)
    return q.order_by(Order.order_date.desc()).offset(offset).limit(limit).all()


@router.get("/{order_id}", response_model=OrderReadWithItems)
def get_order(order_id: UUID, db: DB, current_user: CurrentUser) -> Order:
    """Fetch a single order by ID. Returns 404 if not found or owned by another user."""
    order = db.get(Order, order_id)
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order

