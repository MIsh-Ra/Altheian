"""
AI Detection Pipeline Core Package.
Provides multi-stage preprocessing, tamper detection, and model routing.
"""
from app.core.ai_detection.preprocessor import (
    PreprocessResult,
    count_prose_tokens,
    detect_unicode_tampering,
    mask_citations,
    mask_latex_and_math,
    normalize_pdf_line_wraps,
    preprocess_for_ai_detection,
)

__all__ = [
    "PreprocessResult",
    "count_prose_tokens",
    "detect_unicode_tampering",
    "mask_citations",
    "mask_latex_and_math",
    "normalize_pdf_line_wraps",
    "preprocess_for_ai_detection",
]
