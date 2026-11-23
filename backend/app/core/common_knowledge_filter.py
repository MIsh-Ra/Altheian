import os
import re
import json
import logging
from pathlib import Path
from typing import Tuple, List, Set, Optional

logger = logging.getLogger(__name__)

_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"
_FORMULAS_FILE = _RESOURCES_DIR / "academic_formulas.json"

_afl_set: Optional[Set[str]] = None
_phrase_stems: Optional[List[str]] = None
_empirical_phrases: Optional[List[str]] = None


def _load_academic_corpus():
    global _afl_set, _phrase_stems, _empirical_phrases
    if _afl_set is not None:
        return

    _afl_set = set()
    _phrase_stems = []
    _empirical_phrases = []

    if _FORMULAS_FILE.exists():
        try:
            with open(_FORMULAS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _afl_set = set(data.get("afl_formulas", []))
                _phrase_stems = data.get("academic_phrase_stems", [])
                _empirical_phrases = data.get("empirical_reporting_phrases", [])
        except Exception as e:
            logger.warning(f"Failed to load academic_formulas.json: {e}")
    else:
        logger.warning(f"Academic formulas file not found at {_FORMULAS_FILE}")


# ── POLYGLOT CODE & MATH REGEXES ─────────────────────────────────────────────

# Multi-language keywords and patterns
_POLYGLOT_CODE_PATTERNS = [
    # Python
    r"\bdef\s+[a-zA-Z_]\w*\s*\(",
    r"\bclass\s+[a-zA-Z_]\w*(\s*\(|\s*:)",
    r"\bimport\s+[a-zA-Z_]\w*",
    r"\bfrom\s+[a-zA-Z_]\w*\s+import\b",
    r"\bself\.[a-zA-Z_]\w*",
    r"\btorch\.(randn|tensor|zeros|manual_seed|nn|optim)\b",
    r"\bnp\.(zeros|ones|array|mean|std)\b",
    r"\b__init__\b",
    # C / C++
    r"#include\s*<[a-zA-Z0-9_.]+>",
    r"\bstd::[a-zA-Z_]\w*",
    r"\bint\s+main\s*\(\s*(void|[a-zA-Z0-9_*,\s]*)\)",
    r"\bnullptr\b",
    r"\bcout\s*<<\b",
    r"\btemplate\s*<\s*typename\b",
    # Java / Kotlin / C#
    r"\bpublic\s+(static\s+)?(void|int|String|boolean)\b",
    r"\bSystem\.out\.print(ln)?\(",
    r"@Override\b",
    r"\bnamespace\s+[a-zA-Z_]\w*",
    # JavaScript / TypeScript
    r"\bconst\s+[a-zA-Z_]\w*\s*=",
    r"\blet\s+[a-zA-Z_]\w*\s*=",
    r"\bexport\s+(default\s+)?(function|class|const)\b",
    r"\basync\s+function\b",
    r"\bconsole\.log\(",
    # SQL
    r"\bSELECT\b[\s\S]*?\bFROM\b",
    r"\bINSERT\s+INTO\s+\w+\b",
    r"\bINNER\s+JOIN\s+\w+\b",
    r"\b(GROUP\s+BY|ORDER\s+BY|HAVING)\b",
    r"\b(COUNT|AVG|SUM|MIN|MAX)\s*\([a-zA-Z0-9_.*]+\)",
    # Shell / Bash
    r"#!/bin/(bash|sh|zsh)",
    r"\bset\s+-[eEuo\s]+pipefail\b",
    r"\bpip\s+install\b",
    r"\bgit\s+(commit|push|pull|clone|checkout)\b",
    r"\bsudo\s+apt(-get)?\b",
    # LaTeX Math / Equations
    r"\\begin\{(equation|align|gather|matrix)\*?\}",
    r"\\[a-zA-Z]+\{[^}]*\}",
    r"\\sum_\{[^}]*\}",
    r"\\mathbb\{[A-Z]\}",
    r"\\mathcal\{[A-Z]\}",
    r"\b\w+\s*∈\s*\{[^}]*\}",
    r"∈\s*R\^\{[^}]*\}",
    r"\b\w+\s*=\s*argmax\b",
    # Specific code references like torch.randn(N, 768) or CrossEntropyLoss
    r"\b[a-zA-Z_]\w*\.[a-zA-Z_]\w*\([a-zA-Z0-9_,\s]*\)",
]

_COMPILED_CODE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _POLYGLOT_CODE_PATTERNS]

_EMPIRICAL_METRIC_PATTERNS = [
    re.compile(r"\b\d+(\.\d+)?%\s*(of\b|accuracy|F1|precision|recall|AUC|baseline|synthetic|real|questions|false|true|on-topic|off-topic)", re.IGNORECASE),
    re.compile(r"\baccuracy\s*(=|:|\s*(of|reaches|peaks\s*at)?)\s*\d+(\.\d+)?%?", re.IGNORECASE),
    re.compile(r"\b(precision|recall|f1(-score)?|auc|loss)\s*(=|:)\s*0?\.\d+", re.IGNORECASE),
    re.compile(r"\b(Accuracy|Precision|Recall|F1(-Score)?)\b", re.IGNORECASE),
    re.compile(r"\bp(-value)?\s*([<>=]|value)\s*0?\.\d+", re.IGNORECASE),
    re.compile(r"\b\d+\s*(training|test|validation|sampled|video)\s*(samples|questions|videos|examples|frames|pairs)\b", re.IGNORECASE),
    re.compile(r"\b(ROC\s*AUC|AUC)\s*(of|=|is|reaches)?\s*0\.\d+\b", re.IGNORECASE),
    re.compile(r"\bthreshold\s*(of|at)?\s*(τ|tau|\w+)\s*=\s*0\.\d+\b", re.IGNORECASE),
    re.compile(r"\b(join128|unique256|v5|v6|seed\s*\d|checkpoint)\b", re.IGNORECASE),
    re.compile(r"\b(see\s+)?(Table|Figure|Section|Algorithm|Eq\.)\s*\d+(\s*\.\s*\d+)?\b", re.IGNORECASE),
]


def is_code_or_math_chunk(text: str) -> bool:
    """Detects whether text is primarily code (polyglot) or mathematical equations."""
    if not text:
        return False

    # Check compiled regex patterns
    match_count = 0
    for pat in _COMPILED_CODE_PATTERNS:
        if pat.search(text):
            match_count += 1
            if match_count >= 2:
                return True

    # Punctuation/delimiter density heuristic for code
    # Code typically has high density of { } [ ] ; = -> :: ( )
    code_chars = sum(1 for c in text if c in "{}[]();=><|&!~+-*/^\\")
    total_chars = max(len(text), 1)
    if code_chars / total_chars > 0.08:
        return True

    # Explicit inline code signatures like 'torch.randn' or 'Eq. 2.2'
    if re.search(r"\btorch\.\w+|\bEq\.\s*\d+\.\d+|\bReLU\(|\bCrossEntropyLoss\b", text):
        return True

    return False


def is_empirical_results_chunk(text: str) -> bool:
    """Detects whether text is the author's own empirical measurements, ablation results, or defect audit."""
    if not text:
        return False

    matches = sum(1 for pat in _EMPIRICAL_METRIC_PATTERNS if pat.search(text))
    # If 2 or more empirical result patterns match, this is experiment reporting
    if matches >= 2:
        return True

    # Check for specific phrase overlap with empirical reporting clichés
    _load_academic_corpus()
    text_lower = text.lower()
    for phrase in _empirical_phrases or []:
        if phrase in text_lower:
            return True

    return False


def is_academic_formulaic_chunk(text: str) -> bool:
    """
    Checks if a chunk's substantive token count is heavily composed of formulaic academic transitions
    from the Academic Formulas List (AFL) or standard academic phrase templates.
    """
    if not text:
        return False

    _load_academic_corpus()
    words = text.lower().split()
    if len(words) < 5:
        return True

    text_lower = text.lower()

    # Check if text starts with standard transitions
    transition_starters = [
        "in this paper", "in this study", "in this work", "in this section",
        "as shown in table", "as shown in figure", "as illustrated in",
        "the remainder of this", "the purpose of this", "to evaluate the",
        "in order to", "on the other hand", "it should be noted",
        "results are summarized in", "the ablation in section",
        "critical defects fixed", "definition 1.", "definition 2."
    ]
    for starter in transition_starters:
        if text_lower.strip().startswith(starter):
            return True

    # Count how many AFL formulas occur in this text
    matched_formula_words = 0
    # Check 3-word, 4-word, and 5-word shingles against AFL
    shingle_sizes = [5, 4, 3]
    matched_spans = []

    for size in shingle_sizes:
        for i in range(len(words) - size + 1):
            shingle = " ".join(words[i : i + size])
            if _afl_set and shingle in _afl_set:
                matched_spans.append((i, i + size))

    # Calculate union of matched token indices
    covered_indices = set()
    for start, end in matched_spans:
        for idx in range(start, end):
            covered_indices.add(idx)

    coverage_ratio = len(covered_indices) / max(len(words), 1)
    if coverage_ratio >= 0.40:
        logger.debug(f"Chunk classified as AFL formulaic (coverage: {coverage_ratio:.2f})")
        return True

    # Check Springer phrase stems
    stem_hits = 0
    for stem in _phrase_stems or []:
        if len(stem) >= 15 and stem in text_lower:
            stem_hits += 1
            if stem_hits >= 2:
                return True

    return False


def should_skip_from_web_search(chunk_text: str) -> Tuple[bool, Optional[str]]:
    """
    Main triage gate: determines whether a suspicious chunk should be skipped from web search.
    
    Returns:
        (should_skip: bool, reason: Optional[str])
    """
    if not chunk_text or len(chunk_text.split()) < 15:
        return True, "Too short for meaningful web search (<15 words)"

    # 1. In-text citations check
    from app.core.citation_parser import has_citations
    if has_citations(chunk_text):
        return True, "Contains in-text citation markers (already attributed)"

    # 2. Code & Mathematical notation
    if is_code_or_math_chunk(chunk_text):
        return True, "Code syntax or mathematical formula"

    # 3. Empirical experimental results / ablation study metrics
    if is_empirical_results_chunk(chunk_text):
        return True, "Author empirical results / experimental measurements"

    # 4. Standard academic formulaic transitions & phrasebank clichés
    if is_academic_formulaic_chunk(chunk_text):
        return True, "Common academic formulaic phrase / transition boilerplate"

    return False, None
