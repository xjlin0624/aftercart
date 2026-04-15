import json
import logging
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging

from ..core.settings import get_settings


logger = logging.getLogger(__name__)


def get_firebase_app():
    settings = get_settings()
    if not settings.fcm_enabled:
        return None

    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    if settings.fcm_service_account_json:
        payload = json.loads(settings.fcm_service_account_json)
        cred = credentials.Certificate(payload)
    elif settings.fcm_service_account_file:
        cred = credentials.Certificate(settings.fcm_service_account_file)
    else:
        return None

    return firebase_admin.initialize_app(cred)


def send_fcm_notification(
    *,
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> dict[str, Any]:
    app = get_firebase_app()
    if app is None:
        return {"status": "disabled", "sent": 0, "failed": len(tokens)}
    if not tokens:
        return {"status": "no_tokens", "sent": 0, "failed": 0}

    sent = 0
    failed = 0
    for token in tokens:
        try:
            messaging.send(
                messaging.Message(
                    token=token,
                    notification=messaging.Notification(title=title, body=body),
                    data=data or {},
                ),
                app=app,
            )
            sent += 1
        except Exception as exc:  # pragma: no cover - relies on firebase runtime
            failed += 1
            logger.warning("Failed to send FCM message to token %s: %s", token[-8:], exc)

    return {"status": "sent" if sent else "failed", "sent": sent, "failed": failed}
