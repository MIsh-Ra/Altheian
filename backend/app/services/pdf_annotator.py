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
from datetime import datetime, timezone
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

# Standard Turnitin cyan and academic highlight color palette
RGB_AI_TURNITIN: tuple[float, float, float] = (0.32, 0.78, 0.86)
RGB_ARCHIVE: tuple[float, float, float] = (0.94, 0.27, 0.27)
RGB_PARAPHRASE_TURNITIN: tuple[float, float, float] = (0.98, 0.45, 0.09)
RGB_WEB: tuple[float, float, float] = (0.23, 0.51, 0.96)


def _get_ai_graduated_opacity(prob: float) -> float | None:
    """Return graduated opacity for Turnitin cyan highlight based on probability."""
    if prob < 0.30:
        return None
    if prob < 0.50:
        return 0.35
    if prob < 0.70:
        return 0.60
    return 0.85

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


def _get_pdf_timestamp() -> str:
    """Return ISO 32000-1 compliant PDF date string: D:YYYYMMDDHHmmssZ."""
    return "D:" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%SZ")


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

    # 3. For longer passages (split into sliding n-grams to handle multi-line wraps)
    words = clean_query.split()
    if len(words) >= 4:
        matched: list[pymupdf.Rect] = []
        step = 3
        sub_len = min(6, len(words))
        for i in range(0, len(words) - (sub_len - 1), step):
            subphrase = " ".join(words[i : i + sub_len])
            try:
                sub_rects = page.search_for(subphrase)
                if sub_rects:
                    for r in sub_rects:
                        if not any(abs(r.x0 - ex.x0) < 2 and abs(r.y0 - ex.y0) < 2 for ex in matched):
                            matched.append(r)
            except (RuntimeError, ValueError) as e:
                logger.debug("Subphrase search failed: %s", e)
                continue
        if matched:
            return matched

    return []


def _find_text_across_pages(
    doc: pymupdf.Document,
    query: str,
    target_page: int | None = None,
    max_offset: int = 6,
) -> tuple[int, list[pymupdf.Rect]] | None:
    """Search for text starting at target_page, then adjacent pages, then document-wide.

    Returns (page_idx, rects) if found, or None.
    """
    if not query or not query.strip() or len(doc) == 0:
        return None

    total_pages = len(doc)
    pages_to_check: list[int] = []

    if target_page is not None and 1 <= target_page <= total_pages:
        initial_idx = target_page - 1
        pages_to_check.append(initial_idx)
        for offset in range(1, max_offset + 1):
            plus = initial_idx + offset
            minus = initial_idx - offset
            if 0 <= plus < total_pages:
                pages_to_check.append(plus)
            if 0 <= minus < total_pages:
                pages_to_check.append(minus)
    else:
        pages_to_check = list(range(total_pages))

    checked: set[int] = set()
    for p_idx in pages_to_check:
        if p_idx in checked:
            continue
        checked.add(p_idx)
        rects = _search_text_on_page(doc[p_idx], query)
        if rects:
            return p_idx, rects

    # Document-wide fallback scan if not found in candidate neighborhood
    for p_idx in range(total_pages):
        if p_idx not in checked:
            rects = _search_text_on_page(doc[p_idx], query)
            if rects:
                return p_idx, rects

    return None


def find_original_pdf_path(
    report_data: dict[str, Any] | None = None,
    doc_obj: Any = None,
    explicit_path: str | Path | None = None,
) -> Path | None:
    """Multi-tiered resolver to locate the original uploaded PDF on disk.

    Resolution Strategy:
      1. Direct path check (explicit_path, doc_obj.meta_data["file_path"], or report_data["meta_data"]["file_path"]).
      2. Document UUID match in candidate storage directories.
      3. Safe filename match in candidate storage directories.
      4. Content-addressable SHA-256 hash match across candidate storage directories.
    """
    import hashlib
    import re
    from app.core.config import settings

    # 1. Direct explicit path check
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file():
            return p

    # Extract identification hints
    file_path = None
    archive_path = None
    doc_id = None
    filename = None
    file_hash = None

    if doc_obj:
        if getattr(doc_obj, "file_path", None):
            file_path = str(doc_obj.file_path)
        if getattr(doc_obj, "meta_data", None) and isinstance(doc_obj.meta_data, dict):
            file_path = file_path or doc_obj.meta_data.get("file_path")
            archive_path = doc_obj.meta_data.get("archive_path")
            file_hash = file_hash or doc_obj.meta_data.get("file_hash")
        doc_id = getattr(doc_obj, "id", None)
        filename = getattr(doc_obj, "filename", None)
        file_hash = file_hash or getattr(doc_obj, "file_hash", None)

    if report_data:
        meta = report_data.get("meta_data") or {}
        if isinstance(meta, dict):
            file_path = file_path or meta.get("file_path")
            archive_path = archive_path or meta.get("archive_path")
            file_hash = file_hash or meta.get("file_hash")
        doc_id = doc_id or report_data.get("document_id")
        filename = filename or report_data.get("filename")
        file_hash = file_hash or report_data.get("file_hash")

    for direct_candidate in (file_path, archive_path):
        if direct_candidate:
            p = Path(direct_candidate)
            if p.is_file() and p.stat().st_size > 0:
                return p

    # Candidate directories
    base_dirs: list[Path] = []
    if getattr(settings, "UPLOAD_DIR", None):
        base_dirs.append(Path(settings.UPLOAD_DIR))
        base_dirs.append(Path(settings.UPLOAD_DIR) / "archive")

    curr_file = Path(__file__).resolve()
    for idx in (2, 3, 4):
        if idx < len(curr_file.parents):
            root_candidate = curr_file.parents[idx]
            base_dirs.append(root_candidate / "uploads")
            base_dirs.append(root_candidate / "uploads" / "archive")
            base_dirs.append(root_candidate / "test_documents")
            base_dirs.append(root_candidate / "Alethian_documents")
            base_dirs.append(root_candidate / "backend" / "uploads")
            base_dirs.append(root_candidate / "backend" / "uploads" / "archive")

    # De-duplicate while preserving order
    candidate_dirs = [d for i, d in enumerate(base_dirs) if d.is_dir() and d not in base_dirs[:i]]

    # 2. Fast O(1) content-addressable match in archive directories
    if file_hash:
        target_hash = file_hash.lower()
        for cdir in candidate_dirs:
            direct_hash_file = cdir / f"{target_hash}.pdf"
            if direct_hash_file.is_file() and direct_hash_file.stat().st_size > 0:
                return direct_hash_file
            direct_archive_file = cdir / "archive" / f"{target_hash}.pdf"
            if direct_archive_file.is_file() and direct_archive_file.stat().st_size > 0:
                return direct_archive_file

    # 3. Match by doc_id prefix/contains
    if doc_id:
        for cdir in candidate_dirs:
            for m in cdir.glob(f"*{doc_id}*"):
                if m.is_file() and m.suffix.lower() == ".pdf" and m.stat().st_size > 0:
                    return m

    # 4. Match by filename / sanitized filename
    if filename:
        clean_name = Path(filename).name
        safe_name = re.sub(r"[^\w\-.]", "_", clean_name)
        for cdir in candidate_dirs:
            exact = cdir / clean_name
            if exact.is_file() and exact.stat().st_size > 0:
                return exact
            exact_safe = cdir / safe_name
            if exact_safe.is_file() and exact_safe.stat().st_size > 0:
                return exact_safe
            for pattern in (f"*{clean_name}", f"*{safe_name}*"):
                for m in cdir.glob(pattern):
                    if m.is_file() and m.suffix.lower() == ".pdf" and m.stat().st_size > 0:
                        return m

    # 5. Deep content-addressable SHA-256 hash scan across candidate dirs
    if file_hash:
        target_hash = file_hash.lower()
        for cdir in candidate_dirs:
            for pdf_path in cdir.rglob("*.pdf"):
                try:
                    if pdf_path.stat().st_size > 0:
                        h = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
                        if h.lower() == target_hash:
                            logger.info("Recovered document path via SHA-256 match: %s -> %s", target_hash[:12], pdf_path)
                            return pdf_path
                except (OSError, PermissionError):
                    continue

    return None


def _synthesize_student_pdf(report_data: dict[str, Any]) -> pymupdf.Document:
    """Generate a cleanly paginated document from extracted text when original file is unavailable."""
    doc = pymupdf.open()
    page_texts: Sequence[dict[str, Any]] = report_data.get("page_texts") or []

    def _render_page_text(page: pymupdf.Page, text: str, page_num: int, total_pages: int):
        # Header rule and label
        header_rect = pymupdf.Rect(54, 30, 541, 45)
        page.insert_textbox(
            header_rect,
            f"Alethian Forensic Viewer — Document Body (Page {page_num} of {total_pages})",
            fontsize=8,
            fontname="helv",
            color=(0.5, 0.5, 0.5),
        )
        page.draw_line(pymupdf.Point(54, 48), pymupdf.Point(541, 48), color=(0.8, 0.8, 0.8), width=0.5)

        # Body text area
        body_rect = pymupdf.Rect(54, 60, 541, 780)
        # Clean formatting: split into paragraphs and insert with line spacing
        page.insert_textbox(body_rect, text.strip(), fontsize=10, fontname="tiro", color=(0.1, 0.1, 0.1))

        # Footer page number
        footer_rect = pymupdf.Rect(54, 800, 541, 815)
        page.insert_textbox(
            footer_rect,
            str(page_num),
            fontsize=9,
            fontname="helv",
            color=(0.6, 0.6, 0.6),
            align=pymupdf.TEXT_ALIGN_CENTER,
        )

    if page_texts:
        total = len(page_texts)
        for idx, pt in enumerate(page_texts, start=1):
            page = doc.new_page(width=595, height=842)
            _render_page_text(page, pt.get("text") or "", idx, total)
    else:
        doc_text = report_data.get("document_text") or "No document text available."
        words = doc_text.split()
        words_per_page = 350
        page_chunks = [
            " ".join(words[i : i + words_per_page])
            for i in range(0, max(len(words), 1), words_per_page)
        ]
        total = len(page_chunks)
        for idx, chunk in enumerate(page_chunks, start=1):
            page = doc.new_page(width=595, height=842)
            _render_page_text(page, chunk, idx, total)

    if len(doc) > 0:
        first_page = doc[0]
        banner_rect = pymupdf.Rect(54, 15, 541, 30)
        first_page.draw_rect(banner_rect, color=(0.85, 0.45, 0.15), fill=(1.0, 0.96, 0.92))
        first_page.insert_textbox(
            banner_rect,
            "ARCHIVAL NOTICE: Original submitted PDF was unavailable on storage. Text shown below is extracted fallback.",
            fontsize=7.5,
            color=(0.75, 0.25, 0.05),
            fontname="helv",
            align=pymupdf.TEXT_ALIGN_CENTER,
        )

    return doc


def annotate_document_pdf(
    original_pdf_bytes_or_path: str | bytes | io.BytesIO | Path | None,
    report_data: dict[str, Any],
    use_turnitin_cyan: bool = False,
) -> bytes:
    """Open original submitted PDF, annotate with in-situ Turnitin-style highlights, and return bytes.

    Annotations Applied:
      a) AI Writing Passages: Turnitin cyan highlight RGB=(0.32, 0.78, 0.86) with graduated opacity.
      b) Plagiarism Passages: Red (0.94, 0.27, 0.27) for archive, Orange (0.98, 0.45, 0.09) for paraphrase, Blue (0.23, 0.51, 0.96) for web.
      c) Excluded Citations: Green underline annotations for properly cited scholarship.
      d) Institutional Boilerplate: Grey highlight with 'Template Exempted' note.
    """
    doc: pymupdf.Document | None = None

    # Step 1: Open document from provided path or bytes
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

    # Fallback to multi-tier path resolution if direct open failed
    if doc is None or len(doc) == 0:
        recovered = find_original_pdf_path(
            report_data=report_data,
            explicit_path=original_pdf_bytes_or_path if isinstance(original_pdf_bytes_or_path, (str, Path)) else None,
        )
        if recovered and recovered.is_file():
            try:
                doc = pymupdf.open(str(recovered))
                logger.info("Successfully opened recovered original PDF at: %s", recovered)
            except (pymupdf.FileDataError, RuntimeError, OSError, ValueError) as e:
                logger.warning(f"Could not open recovered PDF file {recovered}: {e}")

    if doc is None or len(doc) == 0:
        logger.error(
            "Original submitted thesis PDF could not be found on storage for document %s (hash: %s). Falling back to synthetic layout.",
            report_data.get("document_id"),
            report_data.get("file_hash"),
        )
        doc = _synthesize_student_pdf(report_data)

    ai_det = report_data.get("ai_detection") or {}
    elevated_windows = ai_det.get("elevated_windows") or ai_det.get("windows") or []
    matches = report_data.get("matches") or []
    is_turnitin = use_turnitin_cyan or report_data.get("use_turnitin_cyan", False)

    pdf_date = _get_pdf_timestamp()

    # Step 2: Boilerplate Detection across all pages
    for page in doc:
        for phrase in INSTITUTIONAL_TEMPLATES:
            rects = _search_text_on_page(page, phrase)
            if rects:
                annot = page.add_highlight_annot(rects)
                annot.set_colors(stroke=RGB_BOILERPLATE)
                annot.set_info(
                    title="Template Exempted",
                    content="Institutional Certificate / Declaration Boilerplate (Zero penalty recommended)",
                    creationDate=pdf_date,
                    modDate=pdf_date,
                )
                annot.update()

    # Step 3: AI Writing Passages with Graduated Intensity & Elastic Page Location
    for w in elevated_windows:
        prob = float(w.get("ai_probability") or w.get("prob") or 0.0)
        if prob < 0.25:
            continue

        color = RGB_AI_TURNITIN if is_turnitin else _get_ai_graduated_color(prob)
        if not color:
            continue

        opacity = _get_ai_graduated_opacity(prob) or 0.50
        excerpt = (w.get("excerpt") or w.get("text") or "").strip()
        if not excerpt:
            continue

        found = _find_text_across_pages(doc, excerpt, target_page=w.get("page_number"))
        if not found:
            continue

        found_page_idx, rects = found
        page = doc[found_page_idx]
        annot = page.add_highlight_annot(rects)
        annot.set_colors(stroke=color)
        try:
            annot.set_opacity(opacity)
        except Exception:
            pass
        intensity_label = (
            "High (70%+)"
            if prob >= 0.70
            else ("Medium (50-70%)" if prob >= 0.50 else "Moderate (30-50%)")
        )
        annot.set_info(
            title=f"AI Writing Assessment ({intensity_label})",
            content=f"Probability: {prob*100:.1f}%\nWord Choice Predictability: Elevated",
            creationDate=pdf_date,
            modDate=pdf_date,
        )
        annot.update()

    # Step 4: Plagiarism Passages & Excluded Citations with Elastic Page Location
    drawn_highlight_rects: dict[int, list[pymupdf.Rect]] = {}

    def _filter_novel_rects(p_idx: int, rects: list[pymupdf.Rect]) -> list[pymupdf.Rect]:
        existing = drawn_highlight_rects.setdefault(p_idx, [])
        novel: list[pymupdf.Rect] = []
        for r in rects:
            is_dup = False
            for ex in existing:
                inter = r & ex
                if not inter.is_empty and r.get_area() > 0:
                    if (inter.get_area() / r.get_area()) >= 0.70:
                        is_dup = True
                        break
            if not is_dup:
                novel.append(r)
                existing.append(r)
        return novel

    # Process active plagiarism matches before excluded drafts so active highlights take precedence
    ordered_matches = sorted(
        enumerate(matches, start=1),
        key=lambda pair: bool(pair[1].get("is_excluded")),
    )
    for match_idx, m in ordered_matches:
        sub_text = (m.get("submitted_text") or "").strip()
        if not sub_text:
            continue

        found = _find_text_across_pages(doc, sub_text, target_page=m.get("submitted_page"))
        if not found:
            continue

        found_page_idx, rects = found
        page = doc[found_page_idx]

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
                creationDate=pdf_date,
                modDate=pdf_date,
            )
            annot.update()
            continue

        # Author Draft Exemption: Soft highlight with informational note (deduplicated so text stays readable)
        if is_excluded and ("draft" in exclude_reason or "prior submission" in exclude_reason):
            novel_rects = _filter_novel_rects(found_page_idx, rects)
            if not novel_rects:
                continue
            annot = page.add_highlight_annot(novel_rects)
            annot.set_colors(stroke=(0.20, 0.60, 0.90))
            try:
                annot.set_opacity(0.32)
            except Exception:
                pass
            annot.set_info(
                title=f"Author's Previous Draft [{match_idx}] (Exempted)",
                content="Student's own earlier submission - isolated from plagiarism penalty.",
                creationDate=pdf_date,
                modDate=pdf_date,
            )
            annot.update()
            continue

        # (b) Active Plagiarism Matches: Red (archive) vs Orange (paraphrase) vs Blue (web)
        novel_rects = _filter_novel_rects(found_page_idx, rects)
        if not novel_rects:
            continue

        mtype = (m.get("type") or "").lower()
        src_type = ((m.get("source") or {}).get("type") or "").lower()
        is_paraphrase = "paraphrase" in mtype
        is_web = "web" in mtype or src_type == "web" or bool(m.get("url"))
        is_exact = mtype in ("internal_exact", "exact", "verbatim") or sim >= 90

        if is_paraphrase:
            color = RGB_PARAPHRASE_TURNITIN if is_turnitin else RGB_PARAPHRASE
            mtype_title = "Paraphrased / Modified Match"
        elif is_web:
            color = RGB_WEB
            mtype_title = "Internet / Web Match"
        else:
            color = RGB_ARCHIVE if is_turnitin else RGB_VERBATIM
            mtype_title = "Archive / Institutional Match" if is_turnitin else ("Identical Match (Verbatim)" if is_exact else "Paraphrased / Modified Match")

        annot = page.add_highlight_annot(novel_rects)
        annot.set_colors(stroke=color)
        try:
            annot.set_opacity(0.42)
        except Exception:
            pass
        annot.set_info(
            title=f"Source Match [{match_idx}] — {mtype_title}",
            content=f"{sim}% match with {src_title}",
            creationDate=pdf_date,
            modDate=pdf_date,
        )
        annot.update()

        # Turnitin-style margin badge (NO opaque sticky note blobs covering text!)
        first_rect = novel_rects[0]
        try:
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
