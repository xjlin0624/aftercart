from fastapi import APIRouter, Query
from sqlalchemy import func, select

from .deps import CurrentUser, DB
from ..models.outcome_log import OutcomeLog
from ..schemas.outcome_log import SavingsByAction, SavingsSummary

router = APIRouter(prefix="/savings", tags=["savings"])


@router.get("/summary", response_model=SavingsSummary)
def get_savings_summary(
    db: DB,
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=500),
) -> SavingsSummary:
    """
    Return a savings summary for the authenticated user.

    - total_recovered: sum of recovered_value for confirmed successful actions only.
    - total_actions: count of all outcome log entries.
    - successful_actions: count of entries where was_successful is true.
    - by_action: per-action-type breakdown of successful action count and total recovered.
    - history: most recent outcome log entries, newest first (up to ?limit=N).
    """
    uid = current_user.id

    total_recovered: float = db.execute(
        select(func.coalesce(func.sum(OutcomeLog.recovered_value), 0.0))
        .where(OutcomeLog.user_id == uid)
        .where(OutcomeLog.was_successful.is_(True))
    ).scalar()

    total_actions: int = db.execute(
        select(func.count()).select_from(OutcomeLog).where(OutcomeLog.user_id == uid)
    ).scalar()

    successful_actions: int = db.execute(
        select(func.count())
        .select_from(OutcomeLog)
        .where(OutcomeLog.user_id == uid)
        .where(OutcomeLog.was_successful.is_(True))
    ).scalar()

    by_action_rows = db.execute(
        select(
            OutcomeLog.action_taken,
            func.count().label("count"),
            func.coalesce(func.sum(OutcomeLog.recovered_value), 0.0).label("total_recovered"),
        )
        .where(OutcomeLog.user_id == uid)
        .where(OutcomeLog.was_successful.is_(True))
        .group_by(OutcomeLog.action_taken)
    ).all()

    by_action = [
        SavingsByAction(
            action_taken=row.action_taken,
            count=row.count,
            total_recovered=row.total_recovered,
        )
        for row in by_action_rows
    ]

    history = list(
        db.execute(
            select(OutcomeLog)
            .where(OutcomeLog.user_id == uid)
            .order_by(OutcomeLog.logged_at.desc())
            .limit(limit)
        ).scalars().all()
    )

    return SavingsSummary(
        total_recovered=total_recovered,
        total_actions=total_actions,
        successful_actions=successful_actions,
        by_action=by_action,
        history=history,
    )
