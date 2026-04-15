from datetime import datetime, timezone
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from ..db import session_scope
from ..models import Alert, AlertPriority, PushDeviceToken, UserPreferences
from ..services.fcm import send_fcm_notification


@shared_task(name="send_high_priority_alert_push")
def send_high_priority_alert_push(alert_id: str) -> dict[str, str | int]:
    with session_scope() as session:
        alert = session.get(Alert, UUID(alert_id))
        if alert is None:
            return {"status": "missing_alert", "sent": 0, "failed": 0}
        if alert.priority != AlertPriority.high:
            return {"status": "skipped_non_high_priority", "sent": 0, "failed": 0}

        prefs = session.execute(
            select(UserPreferences).where(UserPreferences.user_id == alert.user_id)
        ).scalar_one_or_none()
        if prefs is None or not prefs.push_notifications_enabled:
            return {"status": "push_disabled", "sent": 0, "failed": 0}

        tokens = session.execute(
            select(PushDeviceToken)
            .where(PushDeviceToken.user_id == alert.user_id)
            .where(PushDeviceToken.is_active.is_(True))
        ).scalars().all()
        token_values = [token.token for token in tokens]

        result = send_fcm_notification(
            tokens=token_values,
            title=alert.title,
            body=alert.body,
            data={
                "alert_id": str(alert.id),
                "alert_type": alert.alert_type.value,
                "priority": alert.priority.value,
            },
        )
        if result["sent"] > 0:
            alert.push_sent_at = datetime.now(timezone.utc)
            session.commit()

        return result
