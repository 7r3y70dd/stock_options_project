"""Celery app instance for worker startup."""

from app.core.celery import celery_app

# Import task modules so @celery_app.task decorators run and tasks register.
import app.workers.tasks  # noqa: F401,E402

__all__ = ["celery_app"]
