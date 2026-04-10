from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from .deps import CurrentUser, DB
from ..models.alert import Alert
from ..models.enums import ActionTaken, AlertStatus
from ..models.order_item import OrderItem
from ..models.outcome_log import OutcomeLog
from ..schemas.outcome_log import OutcomeLogCreate, OutcomeLogRead

router = APIRouter(prefix="/outcomes", tags=["outcomes"])


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
    - When alert_id is provided and action_taken is not pending, the alert is automatically
      marked resolved in the same transaction. Pending actions leave the alert open.
    - order_item_id is inherited from the alert when not explicitly provided.
    """
    alert = None
    if body.alert_id is not None:
        alert = db.get(Alert, body.alert_id)
        if alert is None or alert.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    # Inherit order_item_id from the alert when the caller omits it.
    effective_item_id = body.order_item_id
    if effective_item_id is None and alert is not None:
        effective_item_id = alert.order_item_id

    if effective_item_id is not None:
        item = db.get(OrderItem, effective_item_id)
        if item is None or item.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

    outcome = OutcomeLog(
        user_id=current_user.id,
        alert_id=body.alert_id,
        order_item_id=effective_item_id,
        action_taken=body.action_taken,
        recovered_value=body.recovered_value,
        was_successful=body.was_successful,
        failure_reason=body.failure_reason,
        notes=body.notes,
    )
    db.add(outcome)

    # Only resolve the alert once the user has actually acted — not for pending.
    if alert is not None and body.action_taken != ActionTaken.pending:
        alert.status = AlertStatus.resolved
        if alert.resolved_at is None:
            alert.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(outcome)
    return outcome
