import datetime
import io
from typing import Annotated

from app.core.report_engine import (
    build_summary_stats,
    calculate_contributions,
    generate_page_distribution,
    generate_source_breakdown,
    recalculate_after_exclusion,
)
from app.db.models import (
    AIDetectionResult,
    Document,
    Match,
    Report,
    Source,
)
from app.db.session import get_db
from app.schemas.ai_detection import AIDetectionResponse
from app.schemas.match import MatchCommentRequest, MatchExcludeRequest
from app.schemas.report import (
    FullReportResponse,
    HeatmapPageResponse,
    ReportReviewRequest,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()


def _build_report_data(document_id: str, db: Session) -> dict:
    report = db.query(Report).filter(Report.document_id == document_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    doc = report.document

    matches_dicts = [
        {
            "id": m.id,
            "type": m.type,
            "is_excluded": m.is_excluded,
            "submitted_page": m.submitted_page,
            "source_id": m.source_id,
            "match_length_words": m.match_length_words,
            "submitted_text": m.submitted_text,
            "source_text": m.source_text,
            "source_title": m.source.title if m.source else None,
            "submitted_start_char": m.submitted_start_char,
            "submitted_end_char": m.submitted_end_char,
            "similarity_score": m.similarity,
            "similarity": m.similarity,
            "domain": m.source.domain if m.source else None,
            "is_coherent": False,
            "source": {
                "id": m.source.id if m.source else None,
                "title": m.source.title if m.source else None,
                "domain": m.source.domain if m.source else None,
                "type": m.source.type if m.source else None,
                "url": m.source.url if m.source else None,
                "coverage_percent": m.source.coverage_percent if m.source else None,
            } if m.source else None,
        }
        for m in report.matches
    ]

    page_count = doc.page_count or 1
    summary_stats = build_summary_stats(matches_dicts, page_count)
    contributions = calculate_contributions(matches_dicts, report.doc_word_count or 1)

    # Sources with all computed fields
    source_ids = set(m.source_id for m in report.matches if m.source_id)
    sources = db.query(Source).filter(Source.id.in_(source_ids)).all() if source_ids else []
    sources_serialized = [
        {
            "id": s.id,
            "type": s.type,
            "title": s.title,
            "domain": s.domain,
            "url": s.url,
            "coverage_percent": s.coverage_percent or 0.0,
            "match_count": s.match_count or 0,
            "pages_affected": s.pages_affected or [],
            "is_coherent_source": s.is_coherent_source or False,
        }
        for s in sources
    ]

    # Heatmap — from DB (already persisted at analysis time)
    heatmap_serialized = [
        {
            "page_number": h.page_number,
            "density_score": h.density_score,
            "match_density": h.density_score,        # frontend alias
            "internal_density": h.internal_density or 0.0,
            "web_density": h.web_density or 0.0,
            "color": h.color or "#22c55e",
            "match_count": h.match_count or 0,
            "dominant_type": h.dominant_type or "clean",
        }
        for h in sorted(report.heatmap_pages, key=lambda h: h.page_number)
    ]

    # page_distribution: correct shape for BarChart {page, internal_exact, internal_paraphrase, web}
    page_distribution = generate_page_distribution(matches_dicts, page_count)

    # source_breakdown for PieChart
    source_breakdown = generate_source_breakdown(matches_dicts)

    # page_texts for page-aware frontend rendering
    page_texts = doc.page_texts or []

    # Matches serialized fully for frontend
    matches_serialized = []
    for m in report.matches:
        matches_serialized.append({
            "id": m.id,
            "type": m.type,
            "is_excluded": m.is_excluded,
            "exclude_reason": m.exclude_reason,
            "comment": m.comment,
            "submitted_text": m.submitted_text,
            "source_text": m.source_text,
            "submitted_page": m.submitted_page,
            "source_page": m.source_page,
            "submitted_start_char": m.submitted_start_char,
            "submitted_end_char": m.submitted_end_char,
            "similarity_score": m.similarity,
            "similarity": m.similarity,
            "match_length_words": m.match_length_words,
            "color_code": m.color_code,
            "source_id": m.source_id,
            "source": {
                "id": m.source.id,
                "title": m.source.title,
                "domain": m.source.domain,
                "type": m.source.type,
                "url": m.source.url,
                "coverage_percent": m.source.coverage_percent,
            } if m.source else None,
        })

    # AI Detection result if available
    ai_det = db.query(AIDetectionResult).filter(AIDetectionResult.document_id == document_id).first()
    ai_detection_serialized = None
    if ai_det:
        from app.api.ai_detection import _serialize_ai_result
        ai_detection_serialized = _serialize_ai_result(ai_det)

    return {
        "document_id": document_id,
        "document_title": doc.title,
        "document_author": doc.author,
        "document_text": doc.content,
        "page_texts": page_texts,
        "page_count": page_count,
        "analyzed_at": report.created_at,
        "processing_time_seconds": report.processing_time_seconds or 0,
        "scores": {
            "originality_score": report.score,
            "similarity_score": 100 - report.score if report.score is not None else 0,
            "risk_level": report.risk_level or "low",
            "internal_contribution": contributions["internal_contribution"],
            "web_contribution": contributions["web_contribution"],
        },
        "summary_stats": summary_stats,
        "source_breakdown": source_breakdown,
        "sources": sources_serialized,
        "matches": matches_serialized,
        "heatmap": heatmap_serialized,
        "page_distribution": page_distribution,
        "review": {
            "status": report.status,
            "reviewed_by": report.reviewed_by,
            "reviewed_at": report.reviewed_at,
            "faculty_notes": report.faculty_notes,
            "verdict": report.verdict,
        },
        "ai_detection": ai_detection_serialized,
    }


from app.api.dependencies import get_current_user
from app.db.models import User


@router.get("/{document_id}", response_model=FullReportResponse)
def get_report(document_id: str, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    report = db.query(Report).join(Document).filter(
        Report.document_id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _build_report_data(document_id, db)


@router.get("/{document_id}/ai-detection", response_model=AIDetectionResponse)
def get_report_ai_detection(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
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
            status_code=404, detail="AI detection analysis is pending or has not been run"
        )
    from app.api.ai_detection import _serialize_ai_result

    return _serialize_ai_result(ai_det)


@router.get("/{document_id}/heatmap", response_model=list[HeatmapPageResponse])
def get_heatmap(document_id: str, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    report = db.query(Report).join(Document).filter(
        Report.document_id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return [
        {
            "page_number": h.page_number,
            "density_score": h.density_score,
            "match_density": h.density_score,
            "internal_density": h.internal_density or 0.0,
            "web_density": h.web_density or 0.0,
            "color": h.color or "#22c55e",
            "match_count": h.match_count or 0,
        }
        for h in sorted(report.heatmap_pages, key=lambda h: h.page_number)
    ]


@router.patch("/{document_id}/matches/{match_id}")
def exclude_match(document_id: str, match_id: str, req: MatchExcludeRequest,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    report = db.query(Report).join(Document).filter(
        Report.document_id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.is_excluded = req.is_excluded
    match.exclude_reason = req.reason
    db.commit()

    report = db.query(Report).filter(Report.document_id == document_id).first()
    new_score = recalculate_after_exclusion(report, match_id, db)
    return {"status": "success", "is_excluded": match.is_excluded,
            "updated_originality_score": new_score}


@router.post("/{document_id}/matches/{match_id}/comment")
def comment_match(document_id: str, match_id: str, req: MatchCommentRequest,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    report = db.query(Report).join(Document).filter(
        Report.document_id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.comment = req.comment
    db.commit()
    return {"status": "success", "comment": match.comment}


@router.post("/{document_id}/review")
def review_document(document_id: str, req: ReportReviewRequest,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    report = db.query(Report).join(Document).filter(
        Report.document_id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.verdict = req.verdict
    report.faculty_notes = req.faculty_notes
    report.digital_signature = req.digital_signature
    report.status = "reviewed"
    report.reviewed_at = datetime.datetime.now(datetime.UTC)
    db.commit()
    return {"status": "success", "message": "Document marked as reviewed"}


@router.get("/{document_id}/export-pdf")
@router.get("/{document_id}/export/pdf")
def export_pdf(
    document_id: str,
    mode: str = "bundle",
    include_excluded: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an Alethian forensic PDF audit report.
    - mode="bundle" (default): Executive audit (pages 1-3) stitched with
      the in-situ highlighted student thesis document (pages 4+).
    - mode="summary": Executive audit summary report only.
    """
    report = db.query(Report).join(Document).filter(
        Report.document_id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report_data = _build_report_data(document_id, db)
    from fastapi.responses import StreamingResponse
    summary_buffer = _build_pdf(report_data, include_excluded=include_excluded)

    # Return summary-only if requested
    if mode.lower() == "summary":
        return StreamingResponse(
            summary_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=alethian_summary_{document_id[:8]}.pdf"},
        )

    # Bundle mode: locate original document on disk, annotate in-situ, and stitch
    from pathlib import Path
    from app.core.config import settings
    from app.services.pdf_annotator import annotate_document_pdf, stitch_bundle_pdf

    doc_obj = report.document
    file_path = None
    potential_paths = []

    if doc_obj:
        if getattr(doc_obj, "file_path", None):
            potential_paths.append(Path(doc_obj.file_path))
        if doc_obj.meta_data and isinstance(doc_obj.meta_data, dict):
            if doc_obj.meta_data.get("file_path"):
                potential_paths.append(Path(doc_obj.meta_data["file_path"]))

        upload_dir = Path(settings.UPLOAD_DIR) if getattr(settings, "UPLOAD_DIR", None) else (Path(__file__).resolve().parents[3] / "uploads")
        if upload_dir.exists():
            if doc_obj.filename:
                potential_paths.append(upload_dir / doc_obj.filename)
                potential_paths.extend(list(upload_dir.glob(f"*{doc_obj.filename}")))
            potential_paths.extend(list(upload_dir.glob(f"*{doc_obj.id}*")))

    for p in potential_paths:
        if p and p.is_file():
            file_path = str(p)
            break

    try:
        annotated_thesis_bytes = annotate_document_pdf(file_path, report_data)
        stitched_pdf_bytes = stitch_bundle_pdf(summary_buffer.getvalue(), annotated_thesis_bytes)
        output_buffer = io.BytesIO(stitched_pdf_bytes)
        output_buffer.seek(0)
    except Exception as exc:
        output_buffer = summary_buffer

    return StreamingResponse(
        output_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=alethian_audit_bundle_{document_id[:8]}.pdf"},
    )


def _build_pdf(report_data: dict, include_excluded: bool = False) -> io.BytesIO:
    """
    Full reportlab PDF matching Report_Design_v2 §5 specification with AI Forensics.
    Page 1: Cover & Plagiarism Risk
    Page 2: AI Forensic Analysis & Source Index
    Pages 3+: Match Details with side-by-side comparison
    Last Page: Footer integrity token
    """
    import hashlib
    import html

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    from app.core.glossary import (
        AUTHOR_PREVIOUS_DRAFTS,
        IDENTICAL_MATCH,
        INSTITUTIONAL_REPOSITORY,
        INTERNET_SOURCES,
        PARAPHRASED_MATCH,
        PROPERLY_CITED_SOURCE,
        SENTENCE_RHYTHM_VARIETY,
        TEMPLATE_EXEMPTED,
        WORD_CHOICE_PREDICTABILITY,
        map_legacy_match_type,
        map_legacy_source_type,
    )

    buffer = io.BytesIO()
    PAGE_W, PAGE_H = A4
    MARGIN = 20 * mm

    # ── Colour constants matching Report_Design_v2 §3 ──────────────────────
    RED    = colors.HexColor("#ef4444")
    ORANGE = colors.HexColor("#f97316")
    BLUE   = colors.HexColor("#3b82f6")
    GREEN  = colors.HexColor("#22c55e")
    YELLOW = colors.HexColor("#eab308")
    DARK   = colors.HexColor("#0e0e0e")
    GREY   = colors.HexColor("#9ca3af")
    LIGHT  = colors.HexColor("#f3f4f6")
    # ── Palette: Professional Academic Forensic Palette ──
    DARK   = colors.HexColor("#0f172a")  # Slate 900
    SLATE  = colors.HexColor("#334155")  # Slate 700
    BORDER = colors.HexColor("#cbd5e1")  # Slate 300
    LIGHT  = colors.HexColor("#f8fafc")  # Slate 50
    WHITE  = colors.white
    GREY   = colors.HexColor("#64748b")  # Slate 500
    
    RED    = colors.HexColor("#dc2626")  # Red 600
    ORANGE = colors.HexColor("#ea580c")  # Orange 600
    YELLOW = colors.HexColor("#d97706")  # Amber 600
    GREEN  = colors.HexColor("#16a34a")  # Green 600
    BLUE   = colors.HexColor("#2563eb")  # Blue 600

    MATCH_COLORS = {
        "internal_exact": RED,
        "internal_paraphrase": ORANGE,
        "web": BLUE,
    }

    PAGE_W, PAGE_H = A4
    USABLE_W = PAGE_W - 2 * MARGIN

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 8 * mm,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=13, leading=17,
                        textColor=DARK, spaceAfter=2, fontName="Helvetica-Bold")
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=10.5, leading=14,
                        textColor=DARK, spaceAfter=2, fontName="Helvetica-Bold")
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=8, leading=11,
                          textColor=DARK, spaceAfter=1, fontName="Helvetica")
    body_bold = ParagraphStyle("BodyBold", parent=body, fontName="Helvetica-Bold")
    label = ParagraphStyle("Label", parent=styles["Normal"], fontSize=7, leading=9,
                           textColor=GREY, fontName="Helvetica")
    mono = ParagraphStyle("Mono", parent=styles["Normal"], fontSize=7, leading=9.5,
                          fontName="Courier", textColor=DARK)
    mono_small = ParagraphStyle("MonoSmall", parent=styles["Normal"], fontSize=6.5, leading=8.5,
                                fontName="Courier", textColor=DARK)

    scores = report_data.get("scores", {})
    summary = report_data.get("summary_stats", {})
    originality = scores.get("originality_score") or 0.0
    similarity = scores.get("similarity_score") or 0.0
    risk = (scores.get("risk_level") or "low").upper()
    risk_color = RED if risk == "HIGH" else (YELLOW if risk == "MODERATE" else GREEN)

    matches = report_data.get("matches", [])
    excluded_count = summary.get("excluded_matches", 0)
    if not include_excluded:
        matches = [m for m in matches if not m.get("is_excluded")]

    sources = report_data.get("sources", [])
    ai_det = report_data.get("ai_detection")
    now = datetime.datetime.now(datetime.timezone.utc)
    report_hash = hashlib.sha256(
        f"{report_data.get('document_id')}{now.isoformat()}".encode()
    ).hexdigest()[:16].upper()

    doc_text = report_data.get("document_text") or ""
    word_count = len(doc_text.split()) if doc_text else (summary.get("total_words") or 0)
    char_count = len(doc_text)

    story = []

    # ── HEADER BANNER ────────────────────────────────────────────────────────
    header_table = Table(
        [[
            Paragraph("<b>ALETHIAN FORENSIC REPORT</b><br/><font size=7 color='#94a3b8'>ACADEMIC INTEGRITY & MULTI-STAGE FORENSIC AUDIT ENGINE v3.0</font>",
                      ParagraphStyle("HdrL", fontSize=13, leading=16, textColor=WHITE, fontName="Helvetica-Bold")),
            Paragraph(f"<font size=7 color='#94a3b8'>ANALYSIS DATE</font><br/><b>{now.strftime('%b %d, %Y • %H:%M UTC')}</b>",
                      ParagraphStyle("HdrR", fontSize=8, leading=11, textColor=WHITE, fontName="Helvetica", alignment=TA_RIGHT)),
        ]],
        colWidths=[USABLE_W * 0.65, USABLE_W * 0.35],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 3 * mm))

    # ── DOCUMENT METADATA GRID ───────────────────────────────────────────────
    doc_title = report_data.get("document_title")
    if not doc_title or doc_title.lower() in ("unknown", "unknown title", "unknown title (ocr)"):
        doc_title = report_data.get("filename") or "Submitted Document"

    meta_data = [
        [
            Paragraph("<b>Document Title:</b>", body_bold),
            Paragraph(html.escape(str(doc_title)[:85]), body),
            Paragraph("<b>Total Pages:</b>", body_bold),
            Paragraph(str(report_data.get("page_count") or "—"), body),
        ],
        [
            Paragraph("<b>Author / Submitter:</b>", body_bold),
            Paragraph(html.escape(str(report_data.get("document_author") or "Student / Researcher")[:50]), body),
            Paragraph("<b>Word Count:</b>", body_bold),
            Paragraph(f"{word_count:,} words", body),
        ],
        [
            Paragraph("<b>Audit Identifier:</b>", body_bold),
            Paragraph(str(report_data.get("document_id") or "—")[:32], mono),
            Paragraph("<b>Character Count:</b>", body_bold),
            Paragraph(f"{char_count:,} chars", body),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[36 * mm, 64 * mm, 32 * mm, 48 * mm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT, WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 3.5 * mm))

    # ── DUAL SCORE CARDS (ORIGINALITY & AI GENERATION) ──────────────────────
    ai_prob_val = 0.0
    ai_verdict = "NOT PERFORMED"
    if ai_det and not ai_det.get("abstained"):
        ai_prob_val = round((ai_det.get("overall_ai_prob") or 0.0) * 100.0, 1)
        ai_verdict = (ai_det.get("verdict_label") or ai_det.get("verdict") or "HUMAN").upper()

    ai_color = RED if ai_prob_val >= 60 else (ORANGE if ai_prob_val >= 35 else GREEN)
    card_w = (USABLE_W - 4 * mm) / 2

    # Card 1: Originality Card Content
    card1_content = [
        [Paragraph(f"<b>ORIGINALITY AUDIT</b> &nbsp; <font color='{risk_color.hexval()}'><b>[{risk} RISK]</b></font>",
                   ParagraphStyle("C1H", fontSize=8.5, leading=11, fontName="Helvetica-Bold", textColor=DARK))],
        [Paragraph(f"{round(originality)}%",
                   ParagraphStyle("C1Score", fontSize=26, leading=30, fontName="Helvetica-Bold", textColor=risk_color))],
        [Paragraph(f"{100 - round(originality)}% similarity with external archives • {summary.get('total_matches', 0)} total matches",
                   label)],
    ]
    card1_table = Table(card1_content, colWidths=[card_w - 6 * mm])
    card1_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))

    # Card 2: AI Forensics Card Content
    card2_content = [
        [Paragraph(f"<b>AI GENERATION PROBABILITY</b> &nbsp; <font color='{(ai_color if ai_det else GREY).hexval()}'><b>[{ai_verdict}]</b></font>",
                   ParagraphStyle("C2H", fontSize=8.5, leading=11, fontName="Helvetica-Bold", textColor=DARK))],
        [Paragraph(f"{ai_prob_val}%" if ai_det else "N/A",
                   ParagraphStyle("C2Score", fontSize=26, leading=30, fontName="Helvetica-Bold", textColor=ai_color if ai_det else GREY))],
        [Paragraph("Automated language model stylistic pattern analysis" if ai_det else "AI writing assessment unavailable",
                   label)],
    ]
    card2_table = Table(card2_content, colWidths=[card_w - 6 * mm])
    card2_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))

    score_card_container = Table(
        [[card1_table, card2_table]],
        colWidths=[card_w, card_w],
    )
    score_card_container.setStyle(TableStyle([
        ("BOX", (0, 0), (0, 0), 1.2, risk_color),
        ("BACKGROUND", (0, 0), (0, 0), LIGHT),
        ("BOX", (1, 0), (1, 0), 1.2, ai_color if ai_det else GREY),
        ("BACKGROUND", (1, 0), (1, 0), LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(score_card_container)
    story.append(Spacer(1, 3 * mm))

    # ── "HOW TO READ THIS AUDIT REPORT" LEGEND BOX ────────────────────────────
    legend_title = Paragraph("<b>HOW TO READ THIS AUDIT REPORT & ANNOTATION COLOR KEY</b>",
                             ParagraphStyle("LegTitle", fontSize=8, leading=10, fontName="Helvetica-Bold", textColor=DARK))

    col1_text = (
        "<b>Originality Score:</b> Measures percentage of content uniquely authored without uncredited textual overlap with academic archives.<br/>"
        "<b>AI Writing Assessment:</b> Statistical analysis of language model predictability and sentence rhythm indicative of automated generation."
    )
    col2_text = (
        "<font color='#0da6f2'><b>■ Cyan Highlight:</b></font> AI Writing (Soft 30-50%, Med 50-70%, Vibrant 70%+)<br/>"
        "<font color='#dc2626'><b>■ Red:</b></font> Identical Match &nbsp; "
        "<font color='#ea580c'><b>■ Orange:</b></font> Paraphrased Match<br/>"
        "<font color='#16a34a'><b><u>■ Green Underline:</u></b></font> Cited Scholarship &nbsp; "
        "<font color='#94a3b8'><b>■ Grey:</b></font> Institutional Template"
    )

    legend_content = [
        [legend_title, ""],
        [Paragraph(col1_text, ParagraphStyle("Leg1", fontSize=6.8, leading=9, textColor=SLATE, fontName="Helvetica")),
         Paragraph(col2_text, ParagraphStyle("Leg2", fontSize=6.8, leading=9, textColor=SLATE, fontName="Helvetica"))]
    ]
    legend_table = Table(legend_content, colWidths=[USABLE_W * 0.52, USABLE_W * 0.48])
    legend_table.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
        ("LINEBELOW", (0, 0), (1, 0), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(legend_table)
    story.append(Spacer(1, 3 * mm))

    # ── EXCLUSIONS & CITATION GROUNDING CALLOUTS ──────────────────────────────
    raw_matches_list = report_data.get("matches", [])
    citation_excluded_count = sum(1 for m in raw_matches_list if m.get("is_excluded") and "References" in (m.get("exclude_reason") or ""))
    draft_excluded_count = sum(1 for m in raw_matches_list if m.get("is_excluded") and "Prior Submission" in (m.get("exclude_reason") or ""))
    faculty_excluded_count = excluded_count - (citation_excluded_count + draft_excluded_count)

    if citation_excluded_count > 0:
        cite_callout_data = [[
            Paragraph(
                f"<b>Academic Citation Grounding Notice:</b> {citation_excluded_count} matched passage(s) correspond to sources explicitly documented in the document's references / bibliography. "
                "In strict accordance with academic integrity standards, cited and grounded scholarship is validated and exempted from plagiarism penalties.",
                ParagraphStyle("CiteNotice", fontSize=7.5, leading=10, textColor=colors.HexColor("#065f46"), fontName="Helvetica")
            )
        ]]
        cite_table = Table(cite_callout_data, colWidths=[USABLE_W])
        cite_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#a7f3d0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(cite_table)
        story.append(Spacer(1, 2.5 * mm))

    if draft_excluded_count > 0:
        draft_callout_data = [[
            Paragraph(
                f"<b>Author Draft Isolation Notice:</b> {draft_excluded_count} segment(s) match earlier draft(s) submitted by the same author. "
                "In accordance with academic self-plagiarism isolation rules, these segments are cataloged in the Source Index but excluded from plagiarism penalties.",
                ParagraphStyle("DraftNotice", fontSize=7.5, leading=10, textColor=colors.HexColor("#0369a1"), fontName="Helvetica")
            )
        ]]
        draft_table = Table(draft_callout_data, colWidths=[USABLE_W])
        draft_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f9ff")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#bae6fd")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(draft_table)
        story.append(Spacer(1, 2.5 * mm))

    # ── ARCHIVE CORPUS & PLAGIARISM STATISTICS ──────────────────────────────
    int_pct = scores.get("internal_contribution", 0)
    web_pct = scores.get("web_contribution", 0)
    contrib_data = [
        ["Scholarly & Web Repository", "Contribution", "Unique Sources", "Matched Passages"],
        [INSTITUTIONAL_REPOSITORY, f"{int_pct:.1f}%",
         str(sum(1 for s in sources if s.get("type") == "internal")),
         str(summary.get("internal_exact", 0) + summary.get("internal_paraphrase", 0))],
        [INTERNET_SOURCES, f"{web_pct:.1f}%",
         str(sum(1 for s in sources if s.get("type") == "web")),
         str(summary.get("web_matches", 0))],
    ]
    contrib_table = Table(contrib_data, colWidths=[65 * mm, 35 * mm, 38 * mm, 42 * mm])
    contrib_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, WHITE]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(contrib_table)
    story.append(Spacer(1, 3 * mm))

    # Summary Statistics
    stats_data = [
        [
            Paragraph("<b>Total Matched Segments:</b>", body),
            Paragraph(str(summary.get("total_matches", 0)), body_bold),
            Paragraph("<b>Unique Sources Identified:</b>", body),
            Paragraph(str(summary.get("unique_sources", 0)), body_bold),
        ],
        [
            Paragraph("<b>Identical Matches (Verbatim):</b>", body),
            Paragraph(str(summary.get("internal_exact", 0)), body),
            Paragraph("<b>Paraphrased / Modified:</b>", body),
            Paragraph(str(summary.get("internal_paraphrase", 0)), body),
        ],
        [
            Paragraph("<b>Internet & Online Matches:</b>", body),
            Paragraph(str(summary.get("web_matches", 0)), body),
            Paragraph("<b>Pages with Active Overlap:</b>", body),
            Paragraph(f"{summary.get('pages_with_matches', 0)} / {report_data.get('page_count', '—')}", body),
        ],
        [
            Paragraph("<b>Author Drafts (Exempted):</b>", body),
            Paragraph(str(excluded_count), body),
            Paragraph("<b>Average Match Length:</b>", body),
            Paragraph(f"{summary.get('avg_match_length_words', 0):.0f} words", body),
        ],
    ]
    stats_table = Table(stats_data, colWidths=[46 * mm, 44 * mm, 46 * mm, 44 * mm])
    stats_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 4 * mm))

    # ── AI FORENSIC DIAGNOSTICS & FLAGGED PASSAGES ──────────────────────────
    if ai_det:
        story.append(Paragraph("AI Writing Assessment & Stylistic Breakdown", h2))
        ai_diag_data = [
            ["Metric", "Measured Value", "Reference Baseline", "Status"],
            [
                Paragraph("Word Choice Predictability Index", body_bold),
                Paragraph(f"{ai_det.get('binoculars_ratio', 0.0):.4f}" if ai_det.get('binoculars_ratio') is not None else "N/A", mono),
                Paragraph("Standard human writing baseline: &lt; 0.9015", body),
                Paragraph("<font color='#ea580c'><b>ELEVATED</b></font>" if (ai_det.get('binoculars_ratio') or 0.0) >= 0.9015 else "<font color='#16a34a'><b>NATURAL</b></font>", body),
            ],
            [
                Paragraph("Sentence Rhythm & Structural Variety", body_bold),
                Paragraph(f"{ai_det.get('dna_detect_score', 0.0):.4f}" if ai_det.get('dna_detect_score') is not None else "N/A", mono),
                Paragraph("Natural syntactic pacing & clause variation", body),
                Paragraph("<b>ANALYZED</b>", body),
            ],
            [
                Paragraph("Overall Stylistic Verdict", body_bold),
                Paragraph(html.escape(str(ai_det.get("verdict_label") or "Human Authored")), mono),
                Paragraph("Dual-observer statistical evaluation", body),
                Paragraph(f"<b>{html.escape(str(ai_det.get('verdict_label') or 'Human'))}</b>", body),
            ],
            [
                Paragraph("Analyzed Document Scope", body_bold),
                Paragraph(f"{ai_det.get('prose_token_count', 0):,} prose tokens", body),
                Paragraph(f"Full text verification ({word_count:,} words)", body),
                Paragraph("<b>COMPLETE</b>", body),
            ],
        ]
        ai_table = Table(ai_diag_data, colWidths=[48 * mm, 32 * mm, 66 * mm, 34 * mm])
        ai_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, WHITE]),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(ai_table)
        story.append(Spacer(1, 3 * mm))

        # Flagged AI Passages Table (gives actionable, concrete details!)
        windows = ai_det.get("windows") or []
        elevated_windows = [w for w in windows if (w.get("ai_probability") or 0.0) >= 0.25]
        if not elevated_windows:
            elevated_windows = sorted(windows, key=lambda x: -(x.get("ai_probability") or 0.0))[:6]

        if elevated_windows:
            story.append(Paragraph("<b>Neural Flagged Text Passages (High Likelihood Windows):</b>", body_bold))
            story.append(Spacer(1, 1.5 * mm))
            ai_pass_header = [["Section / Page", "AI Likelihood", "Perplexity", "Flagged Excerpt"]]
            ai_pass_rows = []
            for w in elevated_windows[:8]:  # Top 8 flagged paragraphs
                prob = round((w.get("ai_probability") or 0.0) * 100.0)
                risk_lvl = (w.get("risk_level") or "Elevated").capitalize()
                ppl = f"{w.get('binoculars_score', 0.0):.3f}" if w.get('binoculars_score') else "—"
                exc = html.escape((w.get("excerpt") or "").strip()[:180])
                if len(w.get("excerpt") or "") > 180:
                    exc += "..."
                ai_pass_rows.append([
                    Paragraph(f"Section #{w.get('window_index', 0)+1}<br/><font color='#64748b'>Page {w.get('page_number', 1)}</font>", body),
                    Paragraph(f"<b>{prob}% AI</b><br/><font size=6.5 color='{ORANGE.hexval() if prob < 60 else RED.hexval()}'>{risk_lvl}</font>", body),
                    Paragraph(ppl, mono),
                    Paragraph(f"<i>\"{exc}\"</i>", mono_small),
                ])
            ai_pass_table = Table(
                ai_pass_header + ai_pass_rows,
                colWidths=[24 * mm, 26 * mm, 20 * mm, 110 * mm]
            )
            ai_pass_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), SLATE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(ai_pass_table)
            story.append(Spacer(1, 3.5 * mm))

    # ── SOURCE INDEX DIRECTORY (DEDUPLICATED) ─────────────────────────────────
    story.append(Paragraph("Matched Sources Directory", h2))
    
    # Deduplicate sources by title / url
    dedup_sources = {}
    for s in sources:
        key = (s.get("title") or "").strip() or s.get("url") or s.get("domain") or "Unknown"
        if key not in dedup_sources:
            dedup_sources[key] = {
                "title": s.get("title") or s.get("domain") or "Unknown",
                "url": s.get("url") or "",
                "type": s.get("type", "internal").upper(),
                "coverage_percent": s.get("coverage_percent") or 0.0,
                "match_count": s.get("match_count") or 0,
                "pages_affected": set(s.get("pages_affected") or []),
            }
        else:
            if not dedup_sources[key].get("url") and s.get("url"):
                dedup_sources[key]["url"] = s.get("url")
            dedup_sources[key]["match_count"] += (s.get("match_count") or 0)
            dedup_sources[key]["coverage_percent"] = max(dedup_sources[key]["coverage_percent"], s.get("coverage_percent") or 0.0)
            dedup_sources[key]["pages_affected"].update(s.get("pages_affected") or [])

    if dedup_sources:
        src_header = [["#", "Source Title & Reference", "Category", "Coverage", "Matches", "Affected Pages"]]
        src_rows = []
        for i, s in enumerate(sorted(dedup_sources.values(), key=lambda x: -x["coverage_percent"])[:15]):
            pages_list = sorted(list(s["pages_affected"]))
            pages_str = ", ".join(str(p) for p in pages_list[:8])
            if len(pages_list) > 8:
                pages_str += "..."
            
            title_text = html.escape(s["title"])
            if s.get("url"):
                url_esc = html.escape(s["url"])
                title_cell = Paragraph(
                    f"{title_text}<br/><a href='{url_esc}' color='#2563eb'><font size='6.5'><u>{url_esc[:60]}</u></font></a>",
                    body
                )
            else:
                title_cell = Paragraph(title_text, body)

            src_rows.append([
                str(i + 1),
                title_cell,
                s["type"],
                f"{s['coverage_percent']:.1f}%",
                str(s["match_count"]),
                pages_str or "—",
            ])
        src_table = Table(
            src_header + src_rows,
            colWidths=[8 * mm, 74 * mm, 22 * mm, 20 * mm, 18 * mm, 38 * mm],
        )
        src_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, WHITE]),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (3, 0), (4, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(src_table)
    else:
        story.append(Paragraph("No external sources or previous submissions matched against this document.", body))
    story.append(Spacer(1, 4 * mm))

    # ── MATCH DETAILS / AUDIT EXEMPTION SECTION ──────────────────────────────
    story.append(Paragraph("Plagiarism Match Breakdown", h2))
    
    if not matches:
        if excluded_count > 0:
            clearance_msg = (
                f"All {excluded_count} detected similarities correspond to author drafts or cited references. "
                "No uncredited third-party or internet plagiarism was detected across university repositories, journal archives, or live web search gateways."
            )
        else:
            clearance_msg = (
                "No matching similarities were detected across university repositories, journal archives, or live web search gateways. "
                "The submitted document passed all archive originality checks."
            )
        empty_box = [
            [Paragraph("<b>Repository & Internet Archive Clearance:</b> 0 uncredited external or third-party matches found.", body_bold)],
            [Paragraph(clearance_msg, body)],
        ]
        empty_table = Table(empty_box, colWidths=[USABLE_W])
        empty_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(empty_table)
        story.append(Spacer(1, 4 * mm))
    else:
        # Display top matches
        sorted_matches = sorted(matches, key=lambda m: -(m.get("similarity_score") or m.get("similarity") or 0))[:25]
        for i, m in enumerate(sorted_matches):
            mtype = m.get("type", "web")
            mcolor = MATCH_COLORS.get(mtype, BLUE)
            mtype_label = mtype.replace("_", " ").upper()
            sim = round(m.get("similarity_score") or m.get("similarity") or 0)
            src = m.get("source") or {}
            src_name = src.get("title") or src.get("domain") or "Unknown Source"
            src_url = src.get("url") or ""

            raw_sub = m.get("submitted_text") or ""
            raw_src = m.get("source_text") or ""
            submitted_text = html.escape(raw_sub[:300])
            source_text = html.escape(raw_src[:300])
            # Context classification & guidance
            sub_lower = raw_sub.lower()
            is_template = any(phrase in sub_lower for phrase in [
                "certificate of bonafide work",
                "bonafide certificate",
                "this is to certify that",
                "declaration",
                "submitted in partial fulfillment",
                "all rights reserved",
                "supervision and guidance",
                "bonafide record of work",
            ])
            is_cited = m.get("is_excluded") and ("reference" in (m.get("exclude_reason") or "").lower() or "citation" in (m.get("exclude_reason") or "").lower())
            is_draft = m.get("is_excluded") and ("draft" in (m.get("exclude_reason") or "").lower() or "prior submission" in (m.get("exclude_reason") or "").lower())

            context_badge = ""
            if is_template:
                context_badge = "<br/><font size=6.5 color='#f1f5f9'><b>Institutional Certificate Template • Zero penalty recommended</b></font>"
            elif is_cited:
                context_badge = "<br/><font size=6.5 color='#d1fae5'><b>Properly Cited Source (Exempted)</b></font>"
            elif is_draft:
                context_badge = "<br/><font size=6.5 color='#e0f2fe'><b>Author's Previous Draft (Exempted)</b></font>"

            match_block = []
            header_data = [[
                Paragraph(f"Match #{i+1} — {html.escape(mtype_label)}{context_badge}", ParagraphStyle("MHead", fontSize=8, fontName="Helvetica-Bold", textColor=WHITE, leading=10)),
                Paragraph(f"Page {html.escape(str(m.get('submitted_page', '—')))} • {sim}% similarity", ParagraphStyle("MSub", fontSize=8, fontName="Helvetica", textColor=WHITE, alignment=TA_RIGHT, leading=10)),
            ]]
            header_table = Table(header_data, colWidths=[USABLE_W * 0.65, USABLE_W * 0.35])
            header_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), mcolor),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            match_block.append(header_table)

            src_line = f"<b>Source:</b> {html.escape(src_name[:65])}"
            if src_url:
                url_esc = html.escape(src_url)
                src_line += f" — <a href='{url_esc}' color='#2563eb'><u>{html.escape(src_url[:65])}</u></a>"
            match_block.append(Paragraph(src_line, label))
            match_block.append(Spacer(1, 1 * mm))

            diff_data = [
                [Paragraph("<b>Submitted Text</b>", body_bold), Paragraph("<b>Source Text</b>", body_bold)],
                [Paragraph(submitted_text or "—", mono_small), Paragraph(source_text or "—", mono_small)],
            ]
            col_w = (USABLE_W - 2 * mm) / 2
            diff_table = Table(diff_data, colWidths=[col_w, col_w])
            diff_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            match_block.append(diff_table)
            match_block.append(Spacer(1, 2.5 * mm))
            story.append(KeepTogether(match_block))

    # ── FACULTY REVIEW & SIGN-OFF BLOCK ──────────────────────────────────────
    review = report_data.get("review", {})
    review_data = [
        [
            Paragraph("<b>Faculty Sign-Off & Verification</b>", body_bold),
            Paragraph("<b>Cryptographic Verification Hash:</b> " + f"<font face='Courier'>{report_hash}</font>", body),
        ],
        [
            Paragraph("<b>Reviewed By:</b> " + html.escape(str(review.get("reviewed_by") or "___________________________")), body),
            Paragraph("<b>Date:</b> " + str(review.get("reviewed_at") or "___________________________"), body),
        ],
        [
            Paragraph("<b>Academic Verdict:</b> " + html.escape(str(review.get("verdict") or "___________________________")), body),
            Paragraph("<b>Signature:</b> ___________________________", body),
        ],
    ]
    review_table = Table(review_data, colWidths=[USABLE_W * 0.5, USABLE_W * 0.5])
    review_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(KeepTogether([review_table]))

    # Page header/footer callback
    def _add_page_meta(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GREY)
        title_short = (report_data.get("document_title") or "Report")[:50]
        canvas.drawString(MARGIN, 8 * mm, f"Alethian Forensic Report — {title_short}")
        canvas.drawRightString(PAGE_W - MARGIN, 8 * mm, f"Page {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_add_page_meta, onLaterPages=_add_page_meta)
    buffer.seek(0)
    return buffer


@router.get("/{document_id}/export/json")
def export_json(document_id: str, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    report_obj = db.query(Report).join(Document).filter(
        Report.document_id == document_id,
        Document.user_id == current_user.id
    ).first()
    if not report_obj:
        raise HTTPException(status_code=404, detail="Report not found")
    return _build_report_data(document_id, db)
