"""AI Detection Pipeline Core Package.

Provides multi-stage preprocessing, tamper detection, Stage 1 zero-shot scoring (Binoculars, DNA-DetectLLM),
and Stage 2 escalation & localization (Llama-3-8B IRM, DeBERTa, WCP-NOT change-point detection).
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
