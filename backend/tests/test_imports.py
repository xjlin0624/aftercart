def test_scheduler_import_smoke():
    import backend.app.models  # noqa: F401
    import backend.app.schemas  # noqa: F401
    import backend.app.tasks.price_monitoring  # noqa: F401
from backend.app.workers.celery_app import celery_app

    assert celery_app.main == "aftercart"
