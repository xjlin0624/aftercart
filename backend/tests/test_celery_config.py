from datetime import timedelta

from backend.app.workers.celery_app import celery_app


def test_beat_schedule_contains_expected_cycles():
    schedule = celery_app.conf.beat_schedule

    assert "price-check-cycle" in schedule
    assert schedule["price-check-cycle"]["task"] == "price_check_cycle"
    assert schedule["price-check-cycle"]["schedule"] == timedelta(minutes=15)

