import json
import logging
import os
from typing import Annotated, Any

from app.api.dependencies import get_current_user
from app.db.models import AIDetectionResult, Document, User
from app.db.session import get_db
from app.schemas.ai_detection import AIDetectionResponse, AIDetectionStatusResponse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()


def _serialize_ai_result(ai_det: AIDetectionResult) -> dict[str, Any]:
    """Helper to convert AIDetectionResult ORM model into dictionary matching AIDetectionResponse."""
    tier_labels = {
        "T0_HUMAN": "Tier 0 (Human)",
        "T1_INDETERMINATE": "Tier 1 (Inconclusive)",
        "T2_ELEVATED": "Tier 2 (Mixed AI)",
        "T3_HIGH": "Tier 3 (Elevated AI)",
        "ABSTAINED": "Abstained (Insufficient Length)",
    }
    return {
        "id": ai_det.id,
        "document_id": ai_det.document_id,
        "verdict": ai_det.verdict,
        "verdict_label": tier_labels.get(ai_det.verdict, ai_det.verdict),
        "confidence_score": ai_det.confidence_score,
        "overall_ai_prob": ai_det.overall_ai_prob,
        "ai_probability": ai_det.overall_ai_prob,
        "binoculars_ratio": ai_det.binoculars_ratio,
        "dna_detect_score": ai_det.dna_detect_score,
        "irm_divergence": ai_det.irm_divergence,
        "deberta_prob": ai_det.deberta_prob,
        "tamper_flags": ai_det.tamper_flags or [],
        "prose_token_count": ai_det.prose_token_count,
        "abstained": ai_det.abstained,
        "abstention_reason": ai_det.abstention_reason,
        "latency_ms": ai_det.latency_ms,
        "gpu_device_ids": ai_det.gpu_device_ids or [],
        "windows": [
            {
                "id": w.id,
                "window_index": w.window_index,
                "char_start": w.char_start,
                "char_end": w.char_end,
                "page_number": w.page_number,
                "binoculars_score": w.binoculars_score,
                "dna_score": w.dna_score,
                "risk_level": w.risk_level,
                "ai_probability": round(max(0.0, min(1.0, (w.binoculars_score - 0.98) / 0.16)), 4) if w.binoculars_score is not None else 0.0,
                "excerpt": w.excerpt,
            }
            for w in sorted(ai_det.windows, key=lambda x: x.window_index)
        ],
        "change_points": [],
        "created_at": ai_det.created_at,
    }


@router.get("/{document_id}", response_model=AIDetectionResponse)
def get_ai_detection_result(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Retrieves detailed AI text generation detection analysis for a document."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    ai_det = (
        db.query(AIDetectionResult)
        .filter(AIDetectionResult.document_id == document_id)
        .first()
    )
    if not ai_det:
        raise HTTPException(
            status_code=404,
            detail="AI detection analysis is pending or has not been run for this document",
        )

    return _serialize_ai_result(ai_det)


@router.get("/{document_id}/status", response_model=AIDetectionStatusResponse)
def get_ai_detection_status(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Retrieves live real-time status and progress of the AI detection pipeline."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if result is already persisted in DB
    ai_det = (
        db.query(AIDetectionResult)
        .filter(AIDetectionResult.document_id == document_id)
        .first()
    )
    if ai_det:
        return AIDetectionStatusResponse(
            document_id=document_id,
            status="complete",
            progress=100,
            message=f"AI detection complete ({ai_det.verdict})",
            has_result=True,
        )

    # Check Redis cache for live task status
    try:
        import redis

        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True,
        )
        cached = r.get(f"ai_status_cache:{document_id}")
        if cached:
            data = json.loads(cached)
            return AIDetectionStatusResponse(
                document_id=document_id,
                status=data.get("stage", "processing"),
                progress=int(data.get("progress", 0)),
                message=data.get("message"),
                has_result=False,
            )
    except Exception as e:  # noqa: BLE001
        logger.debug("Redis status check failed: %s", e)

    return AIDetectionStatusResponse(
        document_id=document_id,
        status="pending",
        progress=0,
        message="AI detection task queued",
        has_result=False,
    )


@router.post("/{document_id}/analyze")
def trigger_ai_detection(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Manually dispatches or re-runs AI detection for a document."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.content:
        raise HTTPException(
            status_code=400,
            detail="Document text has not been extracted yet. Ingestion must complete first.",
        )

    try:
        from celery_ai_worker import celery_ai_app

        celery_ai_app.send_task(
            "detect_ai_task", args=[document_id], queue="ai_detection"
        )
        return {"status": "enqueued", "document_id": document_id}
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "Direct celery dispatch failed; executing synchronous fallback: %s",
            e,
        )
        from app.core.ai_detection.orchestrator import AIDetectionOrchestrator

        orchestrator = AIDetectionOrchestrator()
        res = orchestrator.analyze(
            document_id=document_id,
            text=doc.content,
            page_texts=doc.page_texts or [],
            db=db,
        )
        return {
            "status": "complete",
            "document_id": document_id,
            "verdict": res.verdict,
            "overall_ai_prob": res.overall_ai_prob,
        }
