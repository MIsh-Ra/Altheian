import hashlib
import uuid
import datetime
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    DocumentStatus,
    Report,
    Source,
    Match,
    HeatmapPage,
    AIDetectionResult,
    AIDetectionWindow,
)

logger = logging.getLogger(__name__)


def compute_file_hash(content: bytes) -> str:
    """Computes SHA-256 hex digest of document byte content."""
    return hashlib.sha256(content).hexdigest()


def find_cached_document(db: Session, file_hash: str) -> Optional[Document]:
    """
    Finds the most recent completed document with an identical file_hash.
    Must have status == completed and extracted content.
    """
    if not file_hash:
        return None
    return (
        db.query(Document)
        .filter(
            Document.file_hash == file_hash,
            Document.status == DocumentStatus.completed,
            Document.content.isnot(None),
        )
        .order_by(Document.upload_date.desc())
        .first()
    )


def clone_cached_document(
    db: Session,
    source_doc: Document,
    new_doc_id: str,
    filename: str,
    user_id: str,
    course_id: Optional[str] = None,
) -> Document:
    """
    Clones a completed document audit into a new document entry in < 20ms.
    Reuses text extraction, Qdrant vectors, AI forensic scores, and plagiarism matches
    without redundant OCR, vector re-indexing, or GPU passes.
    """
    start_time = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Create cloned Document
    new_doc = Document(
        id=new_doc_id,
        title=source_doc.title,
        author=source_doc.author,
        filename=filename,
        course_id=course_id,
        user_id=user_id,
        file_hash=source_doc.file_hash,
        upload_date=start_time,
        status=DocumentStatus.completed,
        content=source_doc.content,
        page_count=source_doc.page_count,
        page_texts=source_doc.page_texts,
        risk_level=source_doc.risk_level,
        originality_score=source_doc.originality_score,
        meta_data={
            **(source_doc.meta_data or {}),
            "cache_hit": True,
            "cached_from": source_doc.id,
            "cached_at": start_time.isoformat(),
            "ingestion_strategy": "sha256_dedup_cache",
        },
    )
    db.add(new_doc)
    db.flush()

    # 2. Clone Report and child entities
    if source_doc.report:
        source_report = source_doc.report[0]
        new_report = Report(
            id=str(uuid.uuid4()),
            document_id=new_doc_id,
            score=source_report.score,
            risk_level=source_report.risk_level,
            doc_word_count=source_report.doc_word_count,
            status=source_report.status or "unreviewed",
            processing_time_seconds=0,
            digital_signature=source_report.digital_signature,
        )
        db.add(new_report)
        db.flush()

        # Clone Heatmap Pages
        for hp in source_report.heatmap_pages:
            db.add(
                HeatmapPage(
                    id=str(uuid.uuid4()),
                    report_id=new_report.id,
                    page_number=hp.page_number,
                    density_score=hp.density_score,
                    hotspots=hp.hotspots,
                    internal_density=hp.internal_density,
                    web_density=hp.web_density,
                    color=hp.color,
                    match_count=hp.match_count,
                    dominant_type=hp.dominant_type,
                )
            )

        # Clone Sources and Matches
        source_id_map = {}
        for m in source_report.matches:
            new_source_id = None
            if m.source:
                if m.source.id not in source_id_map:
                    new_src = Source(
                        id=str(uuid.uuid4()),
                        url=m.source.url,
                        title=m.source.title,
                        author=m.source.author,
                        type=m.source.type,
                        domain=m.source.domain,
                        document_id=m.source.document_id,
                        report_document_id=new_doc_id,
                        coverage_percent=m.source.coverage_percent,
                        match_count=m.source.match_count,
                        pages_affected=m.source.pages_affected,
                        is_coherent_source=m.source.is_coherent_source,
                    )
                    db.add(new_src)
                    db.flush()
                    source_id_map[m.source.id] = new_src.id
                new_source_id = source_id_map[m.source.id]

            db.add(
                Match(
                    id=str(uuid.uuid4()),
                    report_id=new_report.id,
                    source_id=new_source_id,
                    submitted_text=m.submitted_text,
                    source_text=m.source_text,
                    similarity=m.similarity,
                    is_excluded=m.is_excluded,
                    comment=m.comment,
                    type=m.type,
                    submitted_page=m.submitted_page,
                    source_page=m.source_page,
                    submitted_start_char=m.submitted_start_char,
                    submitted_end_char=m.submitted_end_char,
                    match_length_words=m.match_length_words,
                    exclude_reason=m.exclude_reason,
                    color_code=m.color_code,
                )
            )

    # 3. Clone AI Detection Result and Windows
    if source_doc.ai_detection_result:
        src_ai = source_doc.ai_detection_result
        new_ai = AIDetectionResult(
            id=str(uuid.uuid4()),
            document_id=new_doc_id,
            verdict=src_ai.verdict,
            confidence_score=src_ai.confidence_score,
            overall_ai_prob=src_ai.overall_ai_prob,
            binoculars_ratio=src_ai.binoculars_ratio,
            dna_detect_score=src_ai.dna_detect_score,
            irm_divergence=src_ai.irm_divergence,
            deberta_prob=src_ai.deberta_prob,
            tamper_flags=src_ai.tamper_flags,
            prose_token_count=src_ai.prose_token_count,
            abstained=src_ai.abstained,
            abstention_reason=src_ai.abstention_reason,
            latency_ms=0.0,
            gpu_device_ids=src_ai.gpu_device_ids,
        )
        db.add(new_ai)
        db.flush()

        for w in src_ai.windows:
            db.add(
                AIDetectionWindow(
                    id=str(uuid.uuid4()),
                    detection_result_id=new_ai.id,
                    window_index=w.window_index,
                    char_start=w.char_start,
                    char_end=w.char_end,
                    page_number=w.page_number,
                    binoculars_score=w.binoculars_score,
                    dna_score=w.dna_score,
                    risk_level=w.risk_level,
                    excerpt=w.excerpt,
                )
            )

    db.commit()
    db.refresh(new_doc)
    logger.info(
        f"[DEDUP_CACHE_HIT] Cloned document {source_doc.id} -> {new_doc.id} (hash={source_doc.file_hash[:12]})"
    )
    return new_doc
