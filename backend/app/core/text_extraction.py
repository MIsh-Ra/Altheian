"""
Centralised PDF text extraction with 3-tier fallback:
  1. Grobid (structured parse with sections, metadata, references)
  2. pypdf  (raw text from digitally-generated PDFs)
  3. Tesseract OCR (scanned/image-only PDFs)

All three ingestion paths (celery_worker, ingest_archive, seed_archive)
should use extract_text_from_pdf() instead of their own ad-hoc logic.

Returns page_texts: list of {page, text, char_start, char_end} for
page-aware rendering and accurate heatmap/similarity assignment.
"""
import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def _build_page_texts(pages: List[str]) -> List[Dict[str, Any]]:
    """
    Given a list of per-page text strings, build page_texts + page_boundaries.
    Returns:
        page_texts: [{page, text, char_start, char_end}, ...]
        body_text: single concatenated string (pages joined by double newline)
        page_boundaries: [(char_start, char_end, page_num), ...]
    """
    page_texts = []
    page_boundaries = []
    cursor = 0
    separator = "\n\n"
    sep_len = len(separator)

    for i, text in enumerate(pages):
        page_num = i + 1
        char_start = cursor
        char_end = cursor + len(text)
        page_texts.append({
            "page": page_num,
            "text": text,
            "char_start": char_start,
            "char_end": char_end,
        })
        page_boundaries.append((char_start, char_end, page_num))
        cursor = char_end + sep_len  # account for "\n\n" separator

    body_text = separator.join(p["text"] for p in page_texts)
    return page_texts, body_text, page_boundaries


def extract_with_grobid(file_bytes: bytes, grobid_url: str = "http://localhost:8070") -> Optional[Dict[str, Any]]:
    """Tier 1: Grobid structured parse. Returns parsed dict or None on failure."""
    from app.core.ingestion import GrobidClient
    from app.core.config import settings
    try:
        client = GrobidClient(host=grobid_url)
        parsed = client.process_pdf(file_bytes)
        body_text = parsed.get("body_text", "")
        if not body_text or len(body_text.strip()) < settings.MIN_TEXT_LENGTH:
            logger.warning("Grobid returned very little text (%d chars).", len(body_text))
            return None

        # Build page_texts from Grobid's page-break-aware text
        # GrobidClient now returns page_texts if available
        if parsed.get("page_texts"):
            page_texts = parsed["page_texts"]
            page_boundaries = [
                (pt["char_start"], pt["char_end"], pt["page"])
                for pt in page_texts
            ]
            parsed["page_texts"] = page_texts
            parsed["page_boundaries"] = page_boundaries
        else:
            # Fallback: treat as single page
            page_texts = [{"page": 1, "text": body_text, "char_start": 0, "char_end": len(body_text)}]
            parsed["page_texts"] = page_texts
            parsed["page_boundaries"] = [(0, len(body_text), 1)]

        return parsed
    except Exception as e:
        logger.warning("Grobid extraction failed: %s", e)
        return None


def extract_with_pypdf(file_path: str) -> Optional[Dict[str, Any]]:
    """Tier 2: pypdf raw text extraction. Preserves per-page text with char offsets."""
    try:
        import pypdf
        pages = []
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                # Always append (even if empty) to preserve page count alignment
                pages.append(extracted.strip() if extracted else "")

        from app.core.config import settings

        # Filter: at least some pages must have content
        non_empty = [p for p in pages if p]
        if not non_empty:
            logger.warning("pypdf extracted no text.")
            return None

        combined = "\n\n".join(non_empty)
        if len(combined.strip()) < settings.MIN_TEXT_LENGTH:
            logger.warning("pypdf extracted very little text (%d chars).", len(combined))
            return None

        # Build page-indexed structure from ALL pages (including empty ones,
        # so page numbers align with actual PDF page numbers)
        page_texts, body_text, page_boundaries = _build_page_texts(pages)

        return {
            "body_text": body_text,
            "title": "Unknown Title",
            "page_count": len(pages),
            "page_texts": page_texts,
            "page_boundaries": page_boundaries,
            "sections": [],
            "references": [],
            "extraction_method": "pypdf",
            "confidence": 0.6,
        }
    except Exception as e:
        logger.warning("pypdf extraction failed: %s", e)
        return None


def extract_with_ocr(file_path: str) -> Optional[Dict[str, Any]]:
    """Tier 3: Tesseract OCR via pdf2image. For scanned/image-only PDFs."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as e:
        logger.error("OCR dependencies not installed (pytesseract / pdf2image): %s", e)
        return None

    try:
        from app.core.config import settings
        images = convert_from_path(file_path, dpi=settings.OCR_DPI)
        pages = []
        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, lang='eng')
            pages.append(text.strip() if text else "")

        non_empty = [p for p in pages if p]
        if not non_empty:
            return None

        combined = "\n\n".join(non_empty)
        if len(combined.strip()) < settings.MIN_TEXT_LENGTH:
            logger.warning("OCR extracted very little text (%d chars).", len(combined))
            return None

        page_texts, body_text, page_boundaries = _build_page_texts(pages)

        return {
            "body_text": body_text,
            "title": "Unknown Title (OCR)",
            "page_count": len(pages),
            "page_texts": page_texts,
            "page_boundaries": page_boundaries,
            "sections": [],
            "references": [],
            "extraction_method": "ocr",
            "confidence": 0.4,
        }
    except Exception as e:
        logger.warning("OCR extraction failed: %s", e)
        return None


def extract_with_pymupdf(file_path: str) -> Optional[Dict[str, Any]]:
    """Tier 1.5: PyMuPDF high-fidelity text extraction. Preserves authentic per-page text, paragraphs, and boundaries."""
    try:
        import pymupdf
        from pathlib import Path
        doc = pymupdf.open(file_path)
        pages = []
        for page in doc:
            text = page.get_text("text")
            pages.append(text.strip() if text else "")

        from app.core.config import settings
        non_empty = [p for p in pages if p]
        if not non_empty:
            return None

        combined = "\n\n".join(non_empty)
        if len(combined.strip()) < settings.MIN_TEXT_LENGTH:
            return None

        page_texts, body_text, page_boundaries = _build_page_texts(pages)
        title = doc.metadata.get("title") or "Unknown Title"
        if not title or title.strip() in ("Unknown Title", ""):
            title = Path(file_path).name

        return {
            "body_text": body_text,
            "title": title,
            "page_count": len(pages),
            "page_texts": page_texts,
            "page_boundaries": page_boundaries,
            "sections": [],
            "references": [],
            "extraction_method": "pymupdf",
            "confidence": 0.9,
        }
    except Exception as e:
        logger.warning("PyMuPDF extraction failed: %s", e)
        return None


def get_page_count(file_path: str) -> int:
    """Get actual page count from PyMuPDF or pypdf (not section count)."""
    try:
        import pymupdf
        doc = pymupdf.open(file_path)
        return max(1, len(doc))
    except Exception:
        pass
    try:
        import pypdf
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            return max(1, len(reader.pages))
    except Exception:
        return 1


def extract_text_from_pdf(
    file_path: str,
    grobid_url: str = "http://localhost:8070"
) -> Dict[str, Any]:
    """
    Master extraction function. Tries PyMuPDF (authentic per-page structure) + Grobid (metadata/sections) -> pypdf -> OCR.

    KEY INVARIANT: page_boundaries and page_texts are ALWAYS sourced from authentic PDF page structures (PyMuPDF / pypdf),
    preserving real paragraphs, headings, and formatting rather than arbitrary character slicing.
    """
    page_count = get_page_count(file_path)

    # 1. ALWAYS get authentic per-page text & boundaries from PyMuPDF first
    native_result = extract_with_pymupdf(file_path) or extract_with_pypdf(file_path)

    # 2. Read file bytes for Grobid
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # 3. Grobid parse for academic metadata & sections
    grobid_parsed = extract_with_grobid(file_bytes, grobid_url)

    if grobid_parsed and grobid_parsed.get("body_text", "").strip():
        grobid_pages = grobid_parsed.get("page_texts", [])
        grobid_has_real_pages = len(grobid_pages) > 1

        if grobid_has_real_pages:
            logger.info("Grobid extraction: multi-page structure detected (%d pages).", len(grobid_pages))
            grobid_parsed["page_count"] = max(page_count, len(grobid_pages))
            grobid_parsed["extraction_method"] = "grobid"
            return grobid_parsed
        else:
            # Grobid has single-page or unpaginated text:
            # Prefer authentic per-page text from PyMuPDF if available so each page has authentic text & formatting!
            if native_result and native_result.get("page_count", 0) > 1:
                logger.info(
                    "Grobid unpaginated. Merging Grobid metadata with authentic PyMuPDF per-page text (%d pages).",
                    native_result["page_count"]
                )
                native_result["sections"] = grobid_parsed.get("sections", [])
                native_result["references"] = grobid_parsed.get("references", [])
                if grobid_parsed.get("title") and grobid_parsed["title"] != "Unknown Title":
                    native_result["title"] = grobid_parsed["title"]
                native_result["extraction_method"] = "pymupdf+grobid_meta"
                return native_result
            else:
                grobid_parsed["page_count"] = page_count
                grobid_parsed["extraction_method"] = "grobid"
                return grobid_parsed

    # --- Tier 2: Native PyMuPDF / pypdf ---
    if native_result:
        logger.info("Using authentic native PDF extraction (%s).", native_result.get("extraction_method"))
        return native_result

    # --- Tier 3: Tesseract OCR ---
    result = extract_with_ocr(file_path)
    if result:
        return result

    # --- All tiers failed ---
    logger.error("All extraction methods failed for %s", file_path)
    return {
        "body_text": "",
        "title": "Extraction Failed",
        "page_count": page_count,
        "page_texts": [],
        "page_boundaries": [],
        "sections": [],
        "references": [],
        "extraction_method": "empty",
        "confidence": 0.0,
    }

