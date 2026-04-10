from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .deps import get_current_user, get_db
from ..models.alert import Alert
from ..models.order_item import OrderItem
from ..models.outcome_log import OutcomeLog
from ..models.user import User
from ..schemas.outcome_log import OutcomeLogCreate, OutcomeLogRead

router = APIRouter(prefix="/outcomes", tags=["outcomes"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=OutcomeLogRead, status_code=status.HTTP_201_CREATED)
def log_outcome(
    body: OutcomeLogCreate,
    db: DB,
    current_user: CurrentUser,
) -> OutcomeLog:
    """
    Log the result of a user action taken on an alert (e.g. price_matched, returned_and_rebought).

    - alert_id and order_item_id are optional but must belong to the current user when provided.
    - recovered_value captures the dollar amount saved by the action.
    """
    if body.alert_id is not None:
        alert = db.get(Alert, body.alert_id)
        if alert is None or alert.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    if body.order_item_id is not None:
        item = db.get(OrderItem, body.order_item_id)
        if item is None or item.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

    outcome = OutcomeLog(
        user_id=current_user.id,
        alert_id=body.alert_id,
        order_item_id=body.order_item_id,
        action_taken=body.action_taken,
        recovered_value=body.recovered_value,
        was_successful=body.was_successful,
        failure_reason=body.failure_reason,
        notes=body.notes,
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome
