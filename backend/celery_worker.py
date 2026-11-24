import os
import sys

# Ensure backend directory is in sys.path for prefork worker subprocesses
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import json

import redis as _redis
from celery import Celery

redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")

celery_app = Celery("worker", broker=redis_url, backend=redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(bind=True, name="run_analysis_pipeline")
def run_analysis_pipeline(
    self,
    document_id: str,
    user_id: str | None = None,
    file_path: str | None = None,
    scan_scope: dict | None = None,
    **kwargs,
):
    import logging

    from app.core.config import settings
    from app.core.report_engine import calculate_originality, generate_heatmap
    from app.core.similarity import index_document, run_similarity
    from app.core.text_extraction import extract_text_from_pdf
    from app.core.web_dragnet import run_dragnet
    from app.db.models import (
        Document,
        DocumentStatus,
        HeatmapPage,
        Match,
        Report,
        Source,
    )
    from app.db.session import SessionLocal

    logger = logging.getLogger(__name__)
    db = SessionLocal()

    # Redis client for status broadcasting
    try:
        _status_redis = _redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True,
        )
    except Exception:  # noqa: BLE001
        _status_redis = None

    def broadcast_status(stage: str, progress: int, message: str = ""):
        if _status_redis:
            try:
                _status_redis.publish(
                    f"doc_status:{document_id}",
                    json.dumps(
                        {"stage": stage, "progress": progress, "message": message}
                    ),
                )
            except Exception:  # noqa: BLE001, S110
                pass

    try:
        # Resolve legacy positional call where file_path was passed as 2nd arg
        if user_id and isinstance(user_id, str) and ("/" in user_id or "\\" in user_id or user_id.endswith(".pdf")):
            file_path = user_id
            user_id = None

        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        # Resolve file_path if not directly supplied
        if not file_path:
            meta = dict(doc.meta_data or {})
            file_path = meta.get("file_path") or meta.get("archive_path")
            if not file_path or not os.path.exists(file_path):
                from app.services.pdf_annotator import find_original_pdf_path
                recovered = find_original_pdf_path(doc_obj=doc)
                if recovered and recovered.is_file():
                    file_path = str(recovered)

        # Resolve selective audit scope (default all True)
        if scan_scope is None:
            scan_scope = (doc.meta_data or {}).get("scan_scope")
        if not isinstance(scan_scope, dict):
            scan_scope = {}

        check_ai = scan_scope.get("check_ai", True)
        check_web = scan_scope.get("check_web", True)
        check_internal = scan_scope.get("check_internal", True)

        resolved_scope = {
            "check_ai": check_ai,
            "check_web": check_web,
            "check_internal": check_internal,
        }
        meta = dict(doc.meta_data or {})
        meta["scan_scope"] = resolved_scope
        doc.meta_data = meta
        db.commit()

        # --- File Size Check ---
        if file_path and os.path.exists(file_path):
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > getattr(settings, "MAX_UPLOAD_SIZE_MB", 100):
                doc.status = DocumentStatus.failed
                db.commit()
                return {"error": f"File too large: {file_size_mb:.1f}MB"}

        # --- Stage 1: Ingestion ---
        if not getattr(doc, "file_hash", None) and file_path and os.path.exists(file_path):
            try:
                import hashlib
                with open(file_path, "rb") as f:
                    doc.file_hash = hashlib.sha256(f.read()).hexdigest()
            except Exception as e:
                logger.warning(f"Failed to compute file_hash: {e}")

        # Ensure permanent backup copy in archive directory
        if file_path and os.path.exists(file_path):
            try:
                from pathlib import Path
                import shutil
                fp_path = Path(file_path)
                archive_dir = fp_path.parent / "archive"
                archive_dir.mkdir(parents=True, exist_ok=True)
                if doc.file_hash:
                    archive_file = archive_dir / f"{doc.file_hash}.pdf"
                    if not archive_file.exists() or archive_file.stat().st_size == 0:
                        shutil.copy2(file_path, archive_file)
            except Exception as e:
                logger.warning(f"Failed to ensure archive copy: {e}")

        # Ensure file_path and archive_path are recorded in meta_data
        meta = dict(doc.meta_data or {})
        if file_path:
            meta["file_path"] = os.path.abspath(file_path)
            if doc.file_hash:
                fp_path = Path(file_path)
                meta["archive_path"] = os.path.abspath(str(fp_path.parent / "archive" / f"{doc.file_hash}.pdf"))
                meta["file_hash"] = doc.file_hash
        doc.meta_data = meta

        doc.status = DocumentStatus.processing
        db.commit()
        logger.info(f"[{document_id}] Stage: ingestion (scope: ai={check_ai}, web={check_web}, internal={check_internal})")
        broadcast_status("ingesting", 10, "Parsing PDF with Grobid...")

        parsed = extract_text_from_pdf(file_path, grobid_url=settings.GROBID_URL)
        text = parsed.get("body_text", "").replace("\x00", "")
        page_texts = parsed.get(
            "page_texts", []
        )  # [{page, text, char_start, char_end}]
        if page_texts:
            for pt in page_texts:
                if isinstance(pt, dict) and "text" in pt:
                    pt["text"] = str(pt["text"]).replace("\x00", "")
        page_boundaries = parsed.get(
            "page_boundaries", []
        )  # [(char_start, char_end, page_num)]

        raw_title = str(parsed.get("title") or doc.title or doc.filename or "Submitted Document").replace("\x00", "").strip()
        if raw_title in ["Unknown Title", "Unknown Title (OCR)", ""]:
            raw_title = (doc.filename or "Submitted Document").strip()
        doc.title = raw_title[:250]
        doc.page_count = parsed.get("page_count", 1)

        if not text or len(text.strip()) < 50:
            logger.error(f"[{document_id}] All extraction methods failed.")
            doc.status = DocumentStatus.failed
            db.commit()
            return {"error": "No text could be extracted from this PDF."}

        logger.info(
            f"[{document_id}] Extracted via {parsed.get('extraction_method')} "
            f"({len(text)} chars, {doc.page_count} pages, {len(page_texts)} page_texts)"
        )

        doc.content = text
        doc.page_texts = page_texts  # persist page-indexed text
        db.commit()

        # --- Trigger Parallel AI Detection Pipeline ---
        if check_ai:
            try:
                celery_app.send_task(
                    "detect_ai_task", args=[document_id], queue="ai_detection"
                )
                logger.info(f"[{document_id}] Dispatched parallel AI detection task")
            except Exception as ai_dispatch_err:  # noqa: BLE001
                logger.warning(
                    f"[{document_id}] Failed to dispatch AI detection task: {ai_dispatch_err}"
                )
        else:
            logger.info(f"[{document_id}] AI check skipped per scan_scope (check_ai=False)")
            try:
                from app.db.models import AIDetectionResult
                existing_ai = db.query(AIDetectionResult).filter(AIDetectionResult.document_id == document_id).first()
                if existing_ai:
                    db.delete(existing_ai)
                    db.commit()
            except Exception as e:
                logger.warning(f"Could not clear existing AI detection result: {e}")

        # --- Stage 1.5: Index for future comparisons ---
        logger.info(f"[{document_id}] Stage: indexing")
        broadcast_status("indexing", 25, "Indexing document into archive...")
        index_document(
            document_id,
            text,
            title=doc.title,
            user_id=doc.user_id,
            page_boundaries=page_boundaries,
            page_count=doc.page_count or 1,
        )

        # --- Stage 2: Internal Similarity ---
        internal_matches = []
        if check_internal:
            logger.info(f"[{document_id}] Stage: internal_similarity")
            broadcast_status(
                "internal_similarity", 40, "Comparing against internal archive..."
            )
            internal_matches = run_similarity(
                document_id,
                text,
                db,
                page_boundaries=page_boundaries,
                page_count=doc.page_count or 1,
            )

            # Tag self-submissions / prior drafts by the same author immediately
            for m in internal_matches:
                src_doc_id = m.get("source_document_id")
                if src_doc_id:
                    src_doc = db.query(Document).filter(Document.id == src_doc_id).first()
                    if src_doc:
                        proper_title = src_doc.title or src_doc.filename or "Archive Document"
                        if proper_title in ["Unknown Title", "Unknown Title (OCR)", ""]:
                            proper_title = src_doc.filename or "Archive Document"

                        if doc.user_id and src_doc.user_id == doc.user_id:
                            m["is_self_submission"] = True
                            m["is_excluded"] = True
                            m["exclude_reason"] = f"Prior Submission by same author ({src_doc.filename or 'Draft'})"
                            m["source_title"] = f"Prior Submission: {src_doc.filename or proper_title}"
                        else:
                            m["source_title"] = proper_title
        else:
            logger.info(f"[{document_id}] Internal Qdrant similarity skipped per scan_scope (check_internal=False)")
            broadcast_status("internal_similarity", 40, "Skipping internal archive comparison...")

        # --- Stage 3: Web Dragnet ---
        web_matches = []
        if check_web:
            logger.info(f"[{document_id}] Stage: web_dragnet")
            broadcast_status("web_dragnet", 60, "Searching web sources...")
            grobid_references = parsed.get("references", [])
            web_matches = run_dragnet(
                document_id,
                text,
                internal_matches,
                page_boundaries=page_boundaries,
                page_count=doc.page_count or 1,
                grobid_references=grobid_references,
            )
        else:
            logger.info(f"[{document_id}] Web Dragnet search skipped per scan_scope (check_web=False)")
            broadcast_status("web_dragnet", 60, "Skipping web search...")

        # --- Stage 4: Report Generation ---
        logger.info(f"[{document_id}] Stage: report_generation")
        broadcast_status("report_generation", 85, "Generating originality report...")
        all_raw_matches = internal_matches + web_matches

        doc_word_count = len(text.split())
        score = calculate_originality(all_raw_matches, doc_word_count, doc_text=text)
        risk = "high" if score < 50 else ("moderate" if score < 80 else "low")

        report = Report(
            document_id=doc.id,
            score=score,
            risk_level=risk,
            doc_word_count=doc_word_count,
        )
        db.add(report)
        db.flush()

        # --- Persist Sources with computed coverage stats ---
        source_map = {}  # key -> source_id
        source_matches = {}  # key -> [match dicts]

        for m in all_raw_matches:
            key = m.get("source_document_id") or m.get("url")
            if not key:
                continue
            if key not in source_map:
                src = Source(
                    type="web" if m.get("type") == "web" else "internal",
                    url=m.get("url"),
                    title=m.get("source_title") or m.get("domain", "Unknown Source"),
                    domain=m.get("domain", ""),
                    document_id=m.get("source_document_id"),
                    report_document_id=doc.id,
                )
                db.add(src)
                db.flush()
                source_map[key] = src.id
                source_matches[key] = []
            source_matches[key].append(m)

        # Compute coverage_percent, match_count, pages_affected per source
        for key, src_id in source_map.items():
            src_obj = db.query(Source).filter(Source.id == src_id).first()
            if not src_obj:
                continue
            ms = source_matches[key]
            src_obj.match_count = len(ms)
            src_obj.pages_affected = sorted({m.get("submitted_page", 1) for m in ms})
            # coverage = sum of matched words / total doc words
            total_matched_words = sum(
                len(m.get("submitted_text", "").split()) for m in ms
            )
            src_obj.coverage_percent = round(
                min(100.0, (total_matched_words / max(1, doc_word_count)) * 100), 2
            )

        # --- Persist Matches ---
        for m in all_raw_matches:
            key = m.get("source_document_id") or m.get("url")
            match_record = Match(
                report_id=report.id,
                source_id=source_map.get(key),
                type=m.get("type", "web"),
                submitted_text=m.get("submitted_text", ""),
                source_text=m.get("source_text", ""),
                submitted_page=m.get("submitted_page", 1),
                source_page=m.get("source_page", 1),
                submitted_start_char=m.get("submitted_start_char", 0),
                submitted_end_char=m.get("submitted_end_char", 0),
                similarity=m.get("similarity_score", m.get("score", 0.0) * 100),
                match_length_words=len(m.get("submitted_text", "").split()),
                is_excluded=m.get("is_excluded", False),
                exclude_reason=m.get("exclude_reason"),
            )
            db.add(match_record)

        # --- Generate & Persist Heatmap ---
        heatmap = generate_heatmap(
            all_raw_matches,
            doc.page_count,
            doc_word_count=doc_word_count,
            page_texts=page_texts,
        )
        for h in heatmap:
            hp = HeatmapPage(
                report_id=report.id,
                page_number=h["page_number"],
                density_score=h["density_score"],
                internal_density=h.get("internal_density", 0.0),
                web_density=h.get("web_density", 0.0),
                color=h.get("color", "#22c55e"),
                match_count=h.get("match_count", 0),
                dominant_type=h.get("dominant_type", "clean"),
            )
            db.add(hp)

        doc.status = DocumentStatus.complete
        doc.risk_level = risk
        doc.originality_score = score

        db.commit()

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        broadcast_status("complete", 100, "Analysis complete.")

    except Exception:
        logger.exception("Failed worker operation")
        db.rollback()

        # Rollback Qdrant inserts
        try:
            from app.core.similarity import _get_qdrant
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            qdrant = _get_qdrant()
            if qdrant:
                qdrant.client.delete(
                    collection_name=qdrant.collection_name,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="document_id", match=MatchValue(value=document_id)
                            )
                        ]
                    ),
                )
        except Exception as delete_ex:  # noqa: BLE001
            logger.error(f"Failed to rollback Qdrant changes: {delete_ex}")

        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = DocumentStatus.failed
                db.commit()
        except Exception:  # noqa: BLE001, S110
            pass
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="analyze_document")
def analyze_document(self, document_id: str, file_path: str | None = None, *args, **kwargs):
    """Backward-compatible alias for run_analysis_pipeline."""
    return run_analysis_pipeline(self, document_id, file_path=file_path, *args, **kwargs)
