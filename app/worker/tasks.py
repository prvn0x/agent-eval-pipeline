import asyncio
import logging

from celery.exceptions import Retry
from sqlalchemy.exc import OperationalError

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

_RETRYABLE_EXCEPTIONS = (OperationalError, ConnectionError, asyncio.TimeoutError)


@celery_app.task(name="app.worker.tasks.evaluate_conversation", bind=True, max_retries=3)
def evaluate_conversation(self, conversation_id: str) -> dict:
    async def _run() -> dict:
        from app.db.session import AsyncSessionLocal
        from app.services.evaluation_service import EvaluationService

        async with AsyncSessionLocal() as session:
            service = EvaluationService(session)
            evaluation = await service.run(conversation_id)
            await session.commit()
            return {"evaluation_id": evaluation.id, "status": "completed"}

    try:
        return asyncio.run(_run())
    except Retry:
        raise
    except _RETRYABLE_EXCEPTIONS as exc:
        logger.warning("Transient error evaluating %s (attempt %d): %s",
                       conversation_id, self.request.retries + 1, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    except Exception as exc:
        logger.error("Failed evaluating %s: %s", conversation_id, exc, exc_info=True)
        raise


@celery_app.task(name="app.worker.tasks.run_self_updater", bind=True, max_retries=3)
def run_self_updater(self, agent_version: str) -> dict:
    async def _run() -> dict:
        from app.db.session import AsyncSessionLocal
        from app.services.self_updater_service import SelfUpdaterService

        async with AsyncSessionLocal() as session:
            service = SelfUpdaterService(session)
            saved = await service.run(agent_version)
            await session.commit()
            return {"agent_version": agent_version, "suggestions_saved": saved, "status": "completed"}

    try:
        return asyncio.run(_run())
    except Retry:
        raise
    except _RETRYABLE_EXCEPTIONS as exc:
        logger.warning("Transient error in self-updater for %s (attempt %d): %s",
                       agent_version, self.request.retries + 1, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    except Exception as exc:
        logger.error("Self-updater failed for %s: %s", agent_version, exc, exc_info=True)
        raise


@celery_app.task(name="app.worker.tasks.run_meta_eval", bind=True, max_retries=3)
def run_meta_eval(self) -> dict:
    async def _run() -> dict:
        from app.db.session import AsyncSessionLocal
        from app.services.meta_eval_service import MetaEvalService

        async with AsyncSessionLocal() as session:
            service = MetaEvalService(session)
            result = await service.run()
            await session.commit()
            return {"conversations_analyzed": result.conversations_analyzed, "status": "completed"}

    try:
        return asyncio.run(_run())
    except Retry:
        raise
    except _RETRYABLE_EXCEPTIONS as exc:
        logger.warning("Transient error in meta-eval (attempt %d): %s", self.request.retries + 1, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    except Exception as exc:
        logger.error("Meta-eval failed: %s", exc, exc_info=True)
        raise
