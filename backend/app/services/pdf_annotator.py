"""In-Situ PDF Document Highlighting and Bundle Stitching Service ("The Turnitin Way").

This service loads original submitted thesis PDFs, maps AI writing probabilities and
plagiarism similarity matches directly onto vector PDF coordinates, and adds
standardized academic highlight, underline, and badge annotations with graduated intensity.
"""

from __future__ import annotations

import io
import logging
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pymupdf
from app.core.glossary import (
    RGB_AI_HIGH,
    RGB_AI_LOW,
    RGB_AI_MEDIUM,
    RGB_BOILERPLATE,
    RGB_CITED,
    RGB_PARAPHRASE,
    RGB_VERBATIM,
)

logger = logging.getLogger(__name__)

# Standard institutional boilerplate phrases to detect and exempt
INSTITUTIONAL_TEMPLATES = [
    "certificate of bonafide work",
    "bonafide certificate",
    "this is to certify that the thesis",
    "this is to certify that",
    "bonafide record of work",
    "declaration by the candidate",
    "declaration by candidate",
    "student declaration",
    "submitted in partial fulfillment of the requirements",
    "submitted in partial fulfilment",
    "all rights reserved",
    "supervision and guidance",
    "certificate of original authorship",
    "certificate of originality",
]


def _get_ai_graduated_color(prob: float) -> tuple[float, float, float] | None:
    """Return RGB color for graduated AI highlight intensity based on probability."""
    if prob < 0.30:
        return None
    if prob < 0.50:
        return RGB_AI_LOW       # Soft cyan/teal (0.55, 0.85, 0.95)
    if prob < 0.70:
        return RGB_AI_MEDIUM    # Medium cyan (0.25, 0.75, 0.95)
    return RGB_AI_HIGH          # Vibrant saturated cyan (0.05, 0.65, 0.95)


def _search_text_on_page(page: pymupdf.Page, query: str) -> list[pymupdf.Rect]:
    """Robust multi-pass text search across page coordinates."""
    if not query or not query.strip():
        return []

    clean_query = " ".join(query.split())
    if not clean_query:
        return []

    # 1. Direct search
    try:
        rects = page.search_for(clean_query)
        if rects:
            return rects
    except (RuntimeError, ValueError) as e:
        logger.debug("Direct text search failed: %s", e)

    # 2. Case-insensitive / normalized whitespace search
    try:
        rects = page.search_for(clean_query, flags=pymupdf.TEXT_DEHYPHENATE)
        if rects:
            return rects
    except (RuntimeError, ValueError) as e:
        logger.debug("Dehyphenated search failed: %s", e)

    # 3. For longer passages (split into sliding n-grams)
    words = clean_query.split()
    if len(words) > 6:
        matched: list[pymupdf.Rect] = []
        step = 5
        for i in range(0, len(words) - 4, step):
            subphrase = " ".join(words[i : i + 5])
            try:
                sub_rects = page.search_for(subphrase)
                if sub_rects:
                    matched.extend(sub_rects)
            except (RuntimeError, ValueError) as e:
                logger.debug("Subphrase search failed: %s", e)
                continue
        if matched:
            return matched

    return []


def _synthesize_student_pdf(report_data: dict[str, Any]) -> pymupdf.Document:
    """Generate a clean synthetic document from extracted text when original file is unavailable."""
    doc = pymupdf.open()
    page_texts: Sequence[dict[str, Any]] = report_data.get("page_texts") or []

    if page_texts:
        for pt in page_texts:
            page = doc.new_page(width=595, height=842)  # A4 size in points
            text = pt.get("text") or ""
            # Margin rect for readable text flow
            rect = pymupdf.Rect(54, 54, 541, 788)
            page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    else:
        doc_text = report_data.get("document_text") or "No document text available."
        words = doc_text.split()
        words_per_page = 380
        page_chunks = [
            " ".join(words[i : i + words_per_page])
            for i in range(0, max(len(words), 1), words_per_page)
        ]
        for chunk in page_chunks:
            page = doc.new_page(width=595, height=842)
            rect = pymupdf.Rect(54, 54, 541, 788)
            page.insert_textbox(rect, chunk, fontsize=10, fontname="helv")

    return doc


def annotate_document_pdf(
    original_pdf_bytes_or_path: str | bytes | io.BytesIO | Path | None,
    report_data: dict[str, Any],
) -> bytes:
    """Open original submitted PDF, annotate with in-situ Turnitin-style highlights, and return bytes.

    Annotations Applied:
      a) AI Writing Passages: Graduated intensity cyan highlights with metadata.
      b) Plagiarism Passages: Red (identical) and Orange (paraphrased) highlights with [1], [2] badges.
      c) Excluded Citations: Green underline annotations for properly cited scholarship.
      d) Institutional Boilerplate: Grey highlight with 'Template Exempted' note.
    """
    doc: pymupdf.Document | None = None

    # Step 1: Open or synthesize document
    if isinstance(original_pdf_bytes_or_path, (str, Path)):
        path_str = str(original_pdf_bytes_or_path)
        if os.path.exists(path_str):
            try:
                doc = pymupdf.open(path_str)
            except (pymupdf.FileDataError, RuntimeError, OSError, ValueError) as e:
                logger.warning(f"Could not open PDF file {path_str}: {e}")

    elif isinstance(original_pdf_bytes_or_path, (bytes, io.BytesIO)):
        stream_bytes = (
            original_pdf_bytes_or_path.getvalue()
            if isinstance(original_pdf_bytes_or_path, io.BytesIO)
            else original_pdf_bytes_or_path
        )
        if stream_bytes:
            try:
                doc = pymupdf.open(stream=stream_bytes, filetype="pdf")
            except (pymupdf.FileDataError, RuntimeError, OSError, ValueError) as e:
                logger.warning(f"Could not open PDF from stream: {e}")

    if doc is None or len(doc) == 0:
        doc = _synthesize_student_pdf(report_data)

    ai_det = report_data.get("ai_detection") or {}
    elevated_windows = ai_det.get("elevated_windows") or ai_det.get("windows") or []
    matches = report_data.get("matches") or []

    # Step 2: Iterate over pages and apply vector annotations
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        current_page_num = page_idx + 1

        # ── (d) Institutional Boilerplate Detection ───────────────────────────
        for phrase in INSTITUTIONAL_TEMPLATES:
            rects = _search_text_on_page(page, phrase)
            if rects:
                annot = page.add_highlight_annot(rects)
                annot.set_colors(stroke=RGB_BOILERPLATE)
                annot.set_info(
                    title="Template Exempted",
                    content="Institutional Certificate / Declaration Boilerplate (Zero penalty recommended)",
                )
                annot.update()

        # ── (a) AI Writing Passages with Graduated Intensity ─────────────────
        for w in elevated_windows:
            w_page = w.get("page_number")
            # If page specified, match it; otherwise search page
            if w_page and w_page != current_page_num:
                continue

            prob = float(w.get("ai_probability") or w.get("prob") or 0.0)
            color = _get_ai_graduated_color(prob)
            if not color:
                continue

            excerpt = (w.get("excerpt") or w.get("text") or "").strip()
            if not excerpt:
                continue

            rects = _search_text_on_page(page, excerpt)
            if rects:
                annot = page.add_highlight_annot(rects)
                annot.set_colors(stroke=color)
                intensity_label = (
                    "High (70%+)"
                    if prob >= 0.70
                    else ("Medium (50-70%)" if prob >= 0.50 else "Moderate (30-50%)")
                )
                annot.set_info(
                    title=f"AI Writing Assessment ({intensity_label})",
                    content=f"Probability: {prob*100:.1f}%\nWord Choice Predictability: Elevated",
                )
                annot.update()

        # ── (b & c) Plagiarism Passages & Excluded Citations ───────────────────
        for match_idx, m in enumerate(matches, start=1):
            m_page = m.get("submitted_page")
            if m_page and m_page != current_page_num:
                continue

            sub_text = (m.get("submitted_text") or "").strip()
            if not sub_text:
                continue

            rects = _search_text_on_page(page, sub_text)
            if not rects:
                continue

            is_excluded = bool(m.get("is_excluded"))
            exclude_reason = (m.get("exclude_reason") or "").lower()
            src_title = m.get("source_title") or (m.get("source") or {}).get("title") or "Archived Source"
            sim = round(float(m.get("similarity_score") or m.get("similarity") or 0.0))

            # (c) Excluded Citations: Apply Green Underline
            if is_excluded and ("reference" in exclude_reason or "citation" in exclude_reason):
                annot = page.add_underline_annot(rects)
                annot.set_colors(stroke=RGB_CITED)
                annot.set_info(
                    title=f"Properly Cited Source [{match_idx}] (Exempted)",
                    content=f"Reference: {src_title}\nValidated scholarly citation - zero penalty applied.",
                )
                annot.update()
                continue

            # Author Draft Exemption: Soft highlight with informational note
            if is_excluded and ("draft" in exclude_reason or "prior submission" in exclude_reason):
                annot = page.add_highlight_annot(rects)
                annot.set_colors(stroke=(0.20, 0.60, 0.90))
                annot.set_info(
                    title=f"Author's Previous Draft [{match_idx}] (Exempted)",
                    content="Student's own earlier submission - isolated from plagiarism penalty.",
                )
                annot.update()
                continue

            # (b) Active Plagiarism Matches: Red (verbatim) vs Orange (paraphrased)
            mtype = (m.get("type") or "web").lower()
            is_exact = mtype in ("internal_exact", "exact", "verbatim") or sim >= 90
            color = RGB_VERBATIM if is_exact else RGB_PARAPHRASE
            mtype_title = "Identical Match (Verbatim)" if is_exact else "Paraphrased / Modified Match"

            annot = page.add_highlight_annot(rects)
            annot.set_colors(stroke=color)
            annot.set_info(
                title=f"Source Match [{match_idx}] — {mtype_title}",
                content=f"{sim}% match with {src_title}",
            )
            annot.update()

            # Add Turnitin-style numbered note and margin badge
            first_rect = rects[0]
            try:
                page.add_text_annot(
                    first_rect.tl,
                    f"[{match_idx}] {src_title} ({sim}% match)",
                )
                # Visual numbered badge
                badge_x = max(12.0, first_rect.x0 - 18.0)
                badge_y = max(14.0, first_rect.y0 + 2.0)
                page.insert_text(
                    (badge_x, badge_y),
                    f"[{match_idx}]",
                    fontsize=7.5,
                    color=color,
                    fontname="helv",
                )
            except (RuntimeError, ValueError, OSError) as e:
                logger.debug("Could not add badge annotation: %s", e)

    output_bytes = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return output_bytes


def stitch_bundle_pdf(executive_summary_bytes: bytes, annotated_thesis_bytes: bytes) -> bytes:
    """Stitch ReportLab Executive Summary (Pages 1-3) with Annotated Student Thesis into a single PDF."""
    exec_doc = pymupdf.open(stream=executive_summary_bytes, filetype="pdf")
    thesis_doc = pymupdf.open(stream=annotated_thesis_bytes, filetype="pdf")

    # Insert all pages from the annotated thesis into the executive document
    exec_doc.insert_pdf(thesis_doc)

    merged_bytes = exec_doc.tobytes(deflate=True, garbage=3)
    exec_doc.close()
    thesis_doc.close()
    return merged_bytes
