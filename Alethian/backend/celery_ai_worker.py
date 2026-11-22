import logging
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from celery import Celery

logger = logging.getLogger(__name__)

redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")

celery_ai_app = Celery(
    "ai_worker",
    broker=redis_url,
    backend=redis_url,
)

celery_ai_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "detect_ai_task": {"queue": "ai_detection"},
        "escalate_ai_task": {"queue": "ai_escalation"},
    },
)


@celery_ai_app.task(bind=True, name="detect_ai_task")
def detect_ai_task(self, document_id: str):
    """
    Executes multi-stage AI detection for a document.
    Must be run with --pool=solo on GPU workers:
        celery -A celery_ai_worker.celery_ai_app worker -Q ai_detection,ai_escalation --pool=solo --loglevel=info
    """
    from app.core.ai_detection.orchestrator import AIDetectionOrchestrator
    from app.db.models import Document
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc or not doc.content:
            logger.warning(
                f"[{document_id}] Document not found or has no extracted content for AI detection."
            )
            return {"status": "skipped", "reason": "no content"}

        orchestrator = AIDetectionOrchestrator()
        result = orchestrator.analyze(
            document_id=document_id,
            text=doc.content,
            page_texts=doc.page_texts or [],
            db=db,
        )
        return {
            "status": "complete",
            "document_id": document_id,
            "verdict": result.verdict,
            "overall_ai_prob": result.overall_ai_prob,
            "abstained": result.abstained,
            "latency_ms": result.latency_ms,
        }
    except Exception:
        logger.exception(f"[{document_id}] AI detection task failed")
        db.rollback()
        raise
    finally:
        db.close()
