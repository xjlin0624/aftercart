from datetime import timedelta

from backend.app.workers.celery_app import celery_app


def test_beat_schedule_contains_expected_cycles():
    schedule = celery_app.conf.beat_schedule

    assert "price-check-cycle" in schedule
    assert schedule["price-check-cycle"]["task"] == "price_check_cycle"
    assert schedule["price-check-cycle"]["schedule"] == timedelta(minutes=15)
    assert "subscription-flag-refresh-cycle" in schedule
    assert schedule["subscription-flag-refresh-cycle"]["task"] == "subscription_flag_refresh_cycle"
    assert "delivery-check-cycle" in schedule
    assert schedule["delivery-check-cycle"]["task"] == "delivery_check_cycle"

