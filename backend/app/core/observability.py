import logging

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration

from .settings import get_settings


logger = logging.getLogger(__name__)
_INITIALIZED_SERVICES: set[str] = set()


def init_sentry(service_name: str, *, include_celery: bool = False) -> None:
    settings = get_settings()
    if not settings.sentry_dsn:
        return
    if service_name in _INITIALIZED_SERVICES:
        return

    integrations = [FastApiIntegration()] if service_name == "api" else []
    if include_celery and settings.sentry_enable_celery:
        integrations.append(CeleryIntegration())

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.sentry_release or None,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        integrations=integrations,
    )
    _INITIALIZED_SERVICES.add(service_name)
    logger.info("Initialized Sentry for %s.", service_name)
