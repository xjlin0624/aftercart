from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .deps import get_current_user, get_db
from ..models.alert import Alert
from ..models.enums import AlertStatus
from ..models.user import User
from ..schemas.alert import AlertRead, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["alerts"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=list[AlertRead])
def list_alerts(
    db: DB,
    current_user: CurrentUser,
    alert_status: AlertStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Alert]:
    """
    Return alerts for the authenticated user, newest first.

    Optionally filter by ?status=new|viewed|resolved|dismissed|expired.
    """
    stmt = select(Alert).where(Alert.user_id == current_user.id)
    if alert_status is not None:
        stmt = stmt.where(Alert.status == alert_status)
    stmt = stmt.order_by(Alert.created_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


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
