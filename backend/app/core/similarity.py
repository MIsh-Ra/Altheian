import os
import uuid
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from sentence_transformers import util
import difflib

from .shingling import process_text_into_chunks

logger = logging.getLogger(__name__)

# Legacy RedisLSHIndex Removed in Phase 4. Using Qdrant Exact Searches instead.

class QdrantManager:
    def __init__(self, host=None, port=6333):
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", port))
        self.client = QdrantClient(host=self.host, port=self.port)
        self.collection_name = "document_chunks"
        self._ensure_collection()
    
    def _ensure_collection(self):
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

    def search_exact(self, embedding, limit=10, score_threshold=None, query_filter=None):
        """High-threshold search for exact matches."""
        if score_threshold is None:
            from app.core.config import settings
            score_threshold = settings.SIMILARITY_EXACT_THRESHOLD
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter
        )
    
    def search_semantic(self, embedding, limit=10, score_threshold=None, query_filter=None):
        """Lower-threshold search for paraphrase matches."""
        if score_threshold is None:
            from app.core.config import settings
            score_threshold = settings.SIMILARITY_SEMANTIC_THRESHOLD
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter
        )

# Lazy singleton — avoids crash if Qdrant is unreachable at import time
_qdrant = None

def _get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantManager()
    return _qdrant

def deduplicate(matches):
    unique = []
    seen = set()
    for m in matches:
        key = f"{m['submitted_start_char']}-{m['source_document_id']}"
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique

def run_similarity(document_id, text, db_session, page_boundaries=None, page_count=1):
    chunks = process_text_into_chunks(text, page_boundaries, page_count=page_count)
    
    matched_results = []
    exact_seen = set()  # Track (source_doc_id, submitted_char_start) from exact pass

    # ── Exclude Repeated Documents & Prior Drafts by Same Author ─────────────
    # Ensures in-memory vector plagiarism detection does not match against
    # repeated uploads of the same document or identical file hashes.
    excluded_doc_ids = {document_id}
    if db_session and document_id:
        try:
            from app.db.models import Document
            from sqlalchemy import or_
            current_doc = db_session.query(Document).filter(Document.id == document_id).first()
            if current_doc:
                filters = []
                if current_doc.user_id:
                    if current_doc.file_hash:
                        filters.append((Document.user_id == current_doc.user_id) & (Document.file_hash == current_doc.file_hash))
                    if current_doc.filename:
                        filters.append((Document.user_id == current_doc.user_id) & (Document.filename == current_doc.filename))
                    if current_doc.title and current_doc.title not in ["Unknown Title", "Submitted Document", "Archive Document", ""]:
                        filters.append((Document.user_id == current_doc.user_id) & (Document.title == current_doc.title))
                
                if filters:
                    prior_docs = db_session.query(Document.id).filter(or_(*filters)).all()
                    for (p_id,) in prior_docs:
                        excluded_doc_ids.add(p_id)
        except Exception as e:
            logger.warning(f"Error querying repeated documents for exclusion: {e}")

    query_filter = None
    if excluded_doc_ids:
        from qdrant_client.models import Filter, FieldCondition, MatchAny
        query_filter = Filter(
            must_not=[
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=list(excluded_doc_ids))
                )
            ]
        )
    
    qdrant = _get_qdrant()
    for chunk in chunks:
        # 1. Exact match search (high threshold)
        exact_matches = qdrant.search_exact(chunk["embedding"], query_filter=query_filter)
        for m in exact_matches:
            payload = m.payload
            if payload and payload.get("document_id") not in excluded_doc_ids:
                sm = difflib.SequenceMatcher(None, chunk["text"], payload.get("text", ""))
                src_doc_id = payload.get("document_id")
                exact_seen.add((src_doc_id, chunk["char_start"]))
                from app.core.config import settings
                matched_results.append({
                    "type": "internal_exact" if sm.ratio() > settings.SIMILARITY_EXACT_RATIO else "internal_paraphrase",
                    "submitted_text": chunk["text"],
                    "source_text": payload.get("text", ""),
                    "submitted_page": chunk["page"],        # ← real page
                    "source_page": payload.get("page", 1),  # ← stored page
                    "submitted_start_char": chunk["char_start"],
                    "submitted_end_char": chunk["char_end"],
                    "similarity_score": m.score * 100,
                    "source_document_id": src_doc_id,
                    "source_user_id": payload.get("user_id"),
                    "source_title": payload.get("title") or "Archive Document",
                })
        
        # 2. Semantic search (lower threshold, excludes already-matched)
        semantic_matches = qdrant.search_semantic(chunk["embedding"], query_filter=query_filter)
        for m in semantic_matches:
             payload = m.payload
             if payload and payload.get("document_id") not in excluded_doc_ids:
                 src_doc_id = payload.get("document_id")
                 # Skip if this (source, submitted_chunk) pair was already found in exact pass
                 if (src_doc_id, chunk["char_start"]) in exact_seen:
                     continue
                 matched_results.append({
                     "type": "internal_paraphrase",
                     "submitted_text": chunk["text"],
                     "source_text": payload.get("text", ""),
                     "submitted_page": chunk["page"],
                     "source_page": payload.get("page", 1),
                     "submitted_start_char": chunk["char_start"],
                     "submitted_end_char": chunk["char_end"],
                     "similarity_score": m.score * 100,
                     "source_document_id": src_doc_id,
                     "source_user_id": payload.get("user_id"),
                     "source_title": payload.get("title") or "Archive Document",
                 })
                 
    return deduplicate(matched_results)

def index_document(document_id, text, title="Unknown Document", user_id=None, page_boundaries=None, page_count=1):
    qdrant = _get_qdrant()
    
    # Delete existing vectors for this document to prevent duplicates (F-40)
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    try:
        qdrant.client.delete(
            collection_name=qdrant.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        )
    except Exception as e:
        logger.warning(f"Failed to delete old vectors for {document_id}: {e}")
    
    clean_title = (title or "Archive Document").strip()
    if clean_title in ["Unknown Document", "Unknown Title", "Unknown Title (OCR)", ""]:
        clean_title = "Archive Document"

    chunks = process_text_into_chunks(text, page_boundaries, page_count=page_count)
    points = []
    for c in chunks:
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=c["embedding"],
            payload={
                "document_id": document_id,
                "user_id": user_id,
                "text": c["text"],
                "title": clean_title,
                "page": c["page"]
            }
        ))
    if points:
        qdrant.client.upsert(collection_name=qdrant.collection_name, points=points)
    
    return True
