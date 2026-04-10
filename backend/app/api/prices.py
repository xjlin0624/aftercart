from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from .deps import CurrentUser, DB
from ..models.order_item import OrderItem
from ..models.price_snapshot import PriceSnapshot
from ..schemas.price_snapshot import PriceSnapshotRead

router = APIRouter(prefix="/prices", tags=["prices"])


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
