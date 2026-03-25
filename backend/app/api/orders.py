from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.orm import Session

from .deps import get_current_user, get_db
from ..models.order import Order
from ..models.order_item import OrderItem
from ..models.user import User
from ..schemas.order import OrderCreate, OrderRead
from ..schemas.order_item import OrderItemCreate, OrderItemRead

router = APIRouter(prefix="/orders", tags=["orders"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


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

    db.flush()  # ensure order.id is assigned before inserting items

    # Replace items — delete-then-insert keeps the stored set in sync with the
    # extension's latest capture without needing per-item identity tracking.
    db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
    for item_data in body.items:
        db.add(OrderItem(
            order_id=order.id,
            user_id=current_user.id,
            **item_data.model_dump(),
        ))

    db.commit()
    db.refresh(order)

    response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
    return order
