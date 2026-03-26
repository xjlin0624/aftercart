from datetime import timedelta

from celery import Celery

from ..core import get_settings


settings = get_settings()
celery_app = Celery("aftercart")
celery_app.conf.update(
    broker_url=settings.broker_url,
    result_backend=settings.result_backend,
    task_default_queue="default",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    imports=(
        "backend.app.tasks.price_monitoring",
        "backend.app.tasks.subscriptions",
    ),
    beat_schedule={
        "price-check-cycle": {
            "task": "price_check_cycle",
            "schedule": timedelta(minutes=settings.price_check_interval_minutes),
        },
        "subscription-flag-refresh-cycle": {
            "task": "subscription_flag_refresh_cycle",
            "schedule": timedelta(minutes=settings.subscription_refresh_interval_minutes),
        },
    },
)
celery_app.set_default()
