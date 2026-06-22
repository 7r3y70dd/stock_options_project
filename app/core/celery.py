"""Celery configuration and initialization."""

import logging
from celery import Celery
from celery.signals import task_failure, task_success, task_retry

from app.core.config import config

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "options_tracker",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer=config.CELERY_TASK_SERIALIZER,
    result_serializer=config.CELERY_RESULT_SERIALIZER,
    accept_content=config.CELERY_ACCEPT_CONTENT,
    timezone=config.CELERY_TIMEZONE,
    enable_utc=config.CELERY_ENABLE_UTC,
    task_track_started=config.CELERY_TASK_TRACK_STARTED,
    task_time_limit=config.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=config.CELERY_TASK_SOFT_TIME_LIMIT,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.refresh_market_data": {"queue": "data_fetching"},
        "app.workers.tasks.generate_signals": {"queue": "signal_generation"},
        "app.workers.tasks.monitor_trades": {"queue": "trade_monitoring"},
    },
)


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Handle successful task completion."""
    logger.info(f"Task {sender.name} completed successfully with result: {result}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **kw):
    """Handle task failure."""
    logger.error(
        f"Task {sender.name} (ID: {task_id}) failed with exception: {exception}",
        exc_info=einfo,
        extra={
            "task_args": args,
            "task_kwargs": kwargs,
        },
    )


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwargs):
    """Handle task retry."""
    logger.warning(
        f"Task {sender.name} (ID: {task_id}) is being retried. Reason: {reason}",
        exc_info=einfo,
    )
