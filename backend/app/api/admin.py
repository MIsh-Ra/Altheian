import os
import redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.admin import AdminConfigResponse, AdminConfigUpdate, SimilarityThresholds, WebDragnetConfig, ApiStatus, ArchiveStats
from app.core.config import settings
from app.db.models import Document, Match

router = APIRouter()

# Global mock for config
_memory_config = {
    "similarity_thresholds": {
        "minhash_jaccard": 0.5,
        "semantic_cosine": 0.85,
        "web_match": 0.7
    },
    "web_dragnet": {
        "enabled": True,
        "queries_per_document": 20,
        "rate_limit_rpm": 60
    },
    "serper_api_key": None
}

from app.api.dependencies import require_admin
from app.db.models import User


def _get_redis():
    try:
        return redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
    except Exception:
        return None


@router.get("/config", response_model=AdminConfigResponse)
def get_config(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    # Calculate stats dynamically
    doc_count = db.query(Document).count()
    serper_key = None
    r = _get_redis()
    if r:
        try:
            serper_key = r.get("config:serper_api_key")
        except Exception:
            pass
    active_key = serper_key or _memory_config.get("serper_api_key") or settings.SERPER_API_KEY
    has_key = bool(active_key and active_key not in ("", "PASTE_YOUR_KEY_HERE"))

    return AdminConfigResponse(
        similarity_thresholds=SimilarityThresholds(**_memory_config["similarity_thresholds"]),
        web_dragnet=WebDragnetConfig(**_memory_config["web_dragnet"]),
        api_status=ApiStatus(serper="ok" if has_key else "missing_key"),
        archive_stats=ArchiveStats(
            total_documents=doc_count,
            total_shingles=doc_count * 125, # Dummy assumption
            last_indexed="Recently"
        ),
        serper_api_key=active_key
    )


@router.patch("/config")
def update_config(update: AdminConfigUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    response = {"message": "Configuration updated"}
    if update.similarity_thresholds:
        _memory_config["similarity_thresholds"]["semantic_cosine"] = update.similarity_thresholds.semantic_cosine
        _memory_config["similarity_thresholds"]["minhash_jaccard"] = update.similarity_thresholds.minhash_jaccard
        _memory_config["similarity_thresholds"]["web_match"] = update.similarity_thresholds.web_match
    if update.serper_api_key is not None:
        _memory_config["serper_api_key"] = update.serper_api_key
        r = _get_redis()
        if r:
            try:
                r.set("config:serper_api_key", update.serper_api_key)
            except Exception:
                pass
        response["serper_api_key"] = update.serper_api_key
    return response
