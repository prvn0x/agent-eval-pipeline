from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "agent_eval",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.worker.tasks.evaluate_conversation": {"queue": "evaluations"},
        "app.worker.tasks.run_self_updater": {"queue": "self_updater"},
        "app.worker.tasks.run_meta_eval": {"queue": "meta_eval"},
        "app.worker.tasks.check_regressions": {"queue": "meta_eval"},
    },
    beat_schedule={
        "check-regressions-every-5-minutes": {
            "task": "app.worker.tasks.check_regressions",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)
