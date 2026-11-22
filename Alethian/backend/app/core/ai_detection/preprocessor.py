"""
Stage 0 Academic Preprocessor & Tamper Detection Engine.

Provides deterministic cleaning, normalization, and security auditing for academic documents:
1. UTS #39 Confusable Homoglyph Normalization (Cyrillic/Greek to ASCII).
2. Invisible Unicode Character Stripping (zero-width spaces, joiners, BOM).
3. Tamper Alert Auditing (threshold alert for evasion attempts).
4. Academic LaTeX and Formula Masking -> [MATH].
5. Academic Citation Masking (parenthetical and bracketed) -> [CIT].
6. PDF Extraction Line Wrap & Hyphenation Normalization.
7. Prose Token Counting & Abstention Gate (<150 tokens abstains).
"""
import re
import unicodedata

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Unicode Security: Invisible Characters & UTS #39 Confusables
# ---------------------------------------------------------------------------

INVISIBLE_CHARS: set[str] = {
    "\u200b",  # Zero-width space
    "\u200c",  # Zero-width non-joiner
    "\u200d",  # Zero-width joiner
    "\u2060",  # Word joiner
    "\ufeff",  # Zero-width no-break space / BOM
    "\u00ad",  # Soft hyphen
    "\u200e",  # Left-to-right mark
    "\u200f",  # Right-to-left mark
    "\u202a",  # Left-to-right embedding
    "\u202b",  # Right-to-left embedding
    "\u202c",  # Pop directional formatting
    "\u202d",  # Left-to-right override
    "\u202e",  # Right-to-left override
    "\u2061",  # Function application
    "\u2062",  # Invisible times
    "\u2063",  # Invisible separator
    "\u2064",  # Invisible plus
}

CONFUSABLES_MAP: dict[str, str] = {
    # Cyrillic small letters
    "\u0430": "a",  # Cyrillic small letter a
    "\u0441": "c",  # Cyrillic small letter es
    "\u0434": "d",  # Cyrillic small letter de
    "\u0435": "e",  # Cyrillic small letter ie
    "\u0451": "e",  # Cyrillic small letter io
    "\u0456": "i",  # Cyrillic small letter byelorussian-ukrainian i
    "\u0458": "j",  # Cyrillic small letter je
    "\u043a": "k",  # Cyrillic small letter ka
    "\u043e": "o",  # Cyrillic small letter o
    "\u0440": "p",  # Cyrillic small letter er
    "\u0455": "s",  # Cyrillic small letter dze
    "\u0443": "y",  # Cyrillic small letter u
    "\u0445": "x",  # Cyrillic small letter ha
    "\u0501": "d",  # Cyrillic small letter komi de
    "\u051b": "q",  # Cyrillic small letter qa
    "\u051d": "w",  # Cyrillic small letter we
    # Cyrillic capital letters
    "\u0410": "A",  # Cyrillic capital letter a
    "\u0412": "B",  # Cyrillic capital letter ve
    "\u0421": "C",  # Cyrillic capital letter es
    "\u0415": "E",  # Cyrillic capital letter ie
    "\u041d": "H",  # Cyrillic capital letter en
    "\u0406": "I",  # Cyrillic capital letter byelorussian-ukrainian i
    "\u0408": "J",  # Cyrillic capital letter je
    "\u041a": "K",  # Cyrillic capital letter ka
    "\u041c": "M",  # Cyrillic capital letter em
    "\u041e": "O",  # Cyrillic capital letter o
    "\u0420": "P",  # Cyrillic capital letter er
    "\u0422": "T",  # Cyrillic capital letter te
    "\u0425": "X",  # Cyrillic capital letter ha
    "\u04ae": "Y",  # Cyrillic capital letter straight u
    # Greek small letters
    "\u03b1": "a",  # Greek small letter alpha
    "\u03b5": "e",  # Greek small letter epsilon
    "\u03b9": "i",  # Greek small letter iota
    "\u03ba": "k",  # Greek small letter kappa
    "\u03bd": "v",  # Greek small letter nu
    "\u03bf": "o",  # Greek small letter omicron
    "\u03c1": "p",  # Greek small letter rho
    "\u03c4": "t",  # Greek small letter tau
    "\u03c5": "u",  # Greek small letter upsilon
    "\u03c7": "x",  # Greek small letter chi
    # Greek capital letters
    "\u0391": "A",  # Greek capital letter alpha
    "\u0392": "B",  # Greek capital letter beta
    "\u0395": "E",  # Greek capital letter epsilon
    "\u0396": "Z",  # Greek capital letter zeta
    "\u0397": "H",  # Greek capital letter eta
    "\u0399": "I",  # Greek capital letter iota
    "\u039a": "K",  # Greek capital letter kappa
    "\u039c": "M",  # Greek capital letter mu
    "\u039d": "N",  # Greek capital letter nu
    "\u039f": "O",  # Greek capital letter omicron
    "\u03a1": "P",  # Greek capital letter rho
    "\u03a4": "T",  # Greek capital letter tau
    "\u03a5": "Y",  # Greek capital letter upsilon
    "\u03a7": "X",  # Greek capital letter chi
}

# ---------------------------------------------------------------------------
# Regular Expressions for Academic Masking
# ---------------------------------------------------------------------------

MATH_ENV_REGEX = re.compile(
    r"\\begin\{(?:equation|align|gather|multline|eqnarray|cases|split|matrix|bmatrix|pmatrix|array|math|displaymath)\*?\}.*?\\end\{(?:equation|align|gather|multline|eqnarray|cases|split|matrix|bmatrix|pmatrix|array|math|displaymath)\*?\}",
    re.DOTALL,
)
DISPLAY_BRACKETS_REGEX = re.compile(r"\\\[.*?\\\]", re.DOTALL)
DISPLAY_DOLLARS_REGEX = re.compile(r"\$\$.*?\$\$", re.DOTALL)
INLINE_PARENS_REGEX = re.compile(r"\\\(.*?\\\)", re.DOTALL)
INLINE_DOLLARS_REGEX = re.compile(r"\$(?:\\.|[^\$\n])+?\$")

BRACKET_NUMERIC_CITATION_REGEX = re.compile(
    r"\[\s*\d+(?:[\s,\-–—;]+\d+)*\s*\]"
)
AUTHOR_YEAR_CITATION_REGEX = re.compile(
    r"\((?:(?:\b(?:e\.g\.|i\.e\.|see|cf\.)\s*,?\s*)?[A-Z][A-Za-z\.'`\-]+(?:\s+(?:&|and|[A-Za-z\.'`\-]+))*(?:,\s*|\s+)et\s+al\.?,?\s*(?:18|19|20)\d{2}[a-z]?|(?:\b(?:e\.g\.|i\.e\.|see|cf\.)\s*,?\s*)?[A-Z][A-Za-z\.'`\-]+(?:\s+(?:&|and)\s+[A-Z][A-Za-z\.'`\-]+)?,?\s*(?:18|19|20)\d{2}[a-z]?(?:,\s*(?:18|19|20)\d{2}[a-z]?)*)(?:;\s*(?:(?:\b(?:e\.g\.|i\.e\.|see|cf\.)\s*,?\s*)?[A-Z][A-Za-z\.'`\-]+(?:\s+(?:&|and|[A-Za-z\.'`\-]+))*(?:,\s*|\s+)et\s+al\.?,?\s*(?:18|19|20)\d{2}[a-z]?|(?:\b(?:e\.g\.|i\.e\.|see|cf\.)\s*,?\s*)?[A-Z][A-Za-z\.'`\-]+(?:\s+(?:&|and)\s+[A-Z][A-Za-z\.'`\-]+)?,?\s*(?:18|19|20)\d{2}[a-z]?(?:,\s*(?:18|19|20)\d{2}[a-z]?)*))*\)"
)


# ---------------------------------------------------------------------------
# Pydantic v2 Schema
# ---------------------------------------------------------------------------

class PreprocessResult(BaseModel):
    """Result of Stage 0 Academic Preprocessing and Tamper Detection."""

    cleaned_text: str = Field(
        ...,
        description="Cleaned, normalized, and masked prose text ready for AI detection.",
    )
    prose_token_count: int = Field(
        ...,
        description="Total prose word tokens in the processed text.",
    )
    abstain: bool = Field(
        ...,
        description="True if text fails length or quality gates, meaning detection should abstain.",
    )
    abstain_reason: str | None = Field(
        default=None,
        description="Human-readable reason for abstention if abstain is True.",
    )
    tamper_alert: bool = Field(
        ...,
        description="True if tamper detection count meets or exceeds alert threshold (>= 4).",
    )
    tamper_count: int = Field(
        ...,
        description="Total count of anomalous unicode / invisible / confusable characters detected.",
    )
    tamper_details: list[str] = Field(
        default_factory=list,
        description="Detailed logs of detected tampering characters.",
    )
    latex_regions_masked: int = Field(
        default=0,
        description="Number of LaTeX equations/environments masked to [MATH].",
    )
    citations_masked: int = Field(
        default=0,
        description="Number of citations masked to [CIT].",
    )


# ---------------------------------------------------------------------------
# Pipeline Transformation Functions
# ---------------------------------------------------------------------------

def detect_unicode_tampering(text: str) -> tuple[str, int, list[str]]:
    """Detects invisible characters and UTS #39 confusables (homoglyphs),

    stripping invisible characters, normalizing confusables to ASCII,
    and recording tamper metrics.

    Returns:
        tuple[str, int, list[str]]: (cleaned_text, tamper_count, tamper_details)
    """
    cleaned_chars: list[str] = []
    tamper_count = 0
    tamper_details: list[str] = []

    for idx, ch in enumerate(text):
        if ch in INVISIBLE_CHARS:
            tamper_count += 1
            char_name = unicodedata.name(ch, "INVISIBLE")
            tamper_details.append(
                f"Stripped invisible character U+{ord(ch):04X} ({char_name}) at index {idx}"
            )
            continue

        if ch in CONFUSABLES_MAP:
            tamper_count += 1
            replacement = CONFUSABLES_MAP[ch]
            char_name = unicodedata.name(ch, "CONFUSABLE")
            tamper_details.append(
                f"Normalized confusable character U+{ord(ch):04X} ({char_name}) '{ch}' -> '{replacement}' at index {idx}"
            )
            cleaned_chars.append(replacement)
            continue

        cleaned_chars.append(ch)

    return "".join(cleaned_chars), tamper_count, tamper_details


def normalize_pdf_line_wraps(text: str) -> str:
    """Normalizes PDF extraction artifacts:

    1. Reconnects hyphenated word breaks across newlines (e.g. "algo-\\nrithm" -> "algorithm").
    2. Unwraps hard-wrapped single newlines into spaces while preserving true paragraph boundaries (\\n\\n).
    """
    if not text:
        return ""

    # Normalize carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Reconnect hyphenated word breaks: word- \n word -> wordword
    text = re.sub(r"(\b[a-zA-Z]+)[-\u00AD]\n\s*([a-zA-Z]+\b)", r"\1\2", text)

    # Split by paragraph breaks (\n\s*\n+)
    parts = re.split(r"(\n\s*\n+)", text)
    normalized_parts: list[str] = []

    for part in parts:
        if re.match(r"^\n\s*\n+$", part):
            normalized_parts.append("\n\n")
        else:
            # Replace single newlines and surrounding spaces within paragraph with single space
            unwrapped = re.sub(r"[ \t]*\n[ \t]*", " ", part)
            # Normalize repeated horizontal whitespace
            unwrapped = re.sub(r"[ \t]+", " ", unwrapped).strip()
            if unwrapped:
                normalized_parts.append(unwrapped)

    return "".join(
        p if p == "\n\n" or idx == 0 or normalized_parts[idx - 1] == "\n\n" else " " + p
        for idx, p in enumerate(normalized_parts)
    )


def mask_latex_and_math(text: str) -> tuple[str, int]:
    """Replaces LaTeX environments, display equations, and inline equations with [MATH].

    Returns:
        tuple[str, int]: (masked_text, total_masked_regions)
    """
    total_count = 0

    # 1. LaTeX environments (\begin{equation}...\end{equation}, \begin{align}...\end{align}, etc.)
    text, count = MATH_ENV_REGEX.subn("[MATH]", text)
    total_count += count

    # 2. Display math \[...\]
    text, count = DISPLAY_BRACKETS_REGEX.subn("[MATH]", text)
    total_count += count

    # 3. Display math $$...$$
    text, count = DISPLAY_DOLLARS_REGEX.subn("[MATH]", text)
    total_count += count

    # 4. Inline math \(...\)
    text, count = INLINE_PARENS_REGEX.subn("[MATH]", text)
    total_count += count

    # 5. Inline math $...$
    text, count = INLINE_DOLLARS_REGEX.subn("[MATH]", text)
    total_count += count

    return text, total_count


def mask_citations(text: str) -> tuple[str, int]:
    """Replaces parenthetical citations like "(Smith et al., 2024)" and

    bracketed citations like "[1, 3-5]" with [CIT].

    Returns:
        tuple[str, int]: (masked_text, total_masked_citations)
    """
    total_count = 0

    # 1. Author-year parenthetical citations
    text, count = AUTHOR_YEAR_CITATION_REGEX.subn("[CIT]", text)
    total_count += count

    # 2. Bracketed numeric citations
    text, count = BRACKET_NUMERIC_CITATION_REGEX.subn("[CIT]", text)
    total_count += count

    return text, total_count


def count_prose_tokens(text: str) -> int:
    """Counts word tokens in the prose text, ignoring [MATH] and [CIT] placeholders."""
    if not text:
        return 0
    # Strip masking placeholders
    stripped = re.sub(r"\[(MATH|CIT)\]", "", text)
    tokens = [tok for tok in stripped.split() if tok]
    return len(tokens)


def preprocess_for_ai_detection(raw_text: str, min_tokens: int = 150) -> PreprocessResult:
    """Executes the full Stage 0 Academic Preprocessor & Tamper Detection pipeline:

    1. Unicode tamper detection & confusable normalization (UTS #39)
    2. PDF line wrap and hyphenation normalization
    3. LaTeX and math masking -> [MATH]
    4. Academic citation masking -> [CIT]
    5. Prose token counting & abstention gating
    """
    cleaned_text, tamper_count, tamper_details = detect_unicode_tampering(raw_text)
    cleaned_text = normalize_pdf_line_wraps(cleaned_text)
    cleaned_text, latex_masked = mask_latex_and_math(cleaned_text)
    cleaned_text, citations_masked = mask_citations(cleaned_text)
    prose_tokens = count_prose_tokens(cleaned_text)

    # Tamper alert threshold: >= 4 anomalous characters
    tamper_alert = tamper_count >= 4

    # Abstention gate: insufficient prose length (< min_tokens)
    if prose_tokens < min_tokens:
        abstain = True
        abstain_reason = f"Insufficient prose length (<{min_tokens} tokens)"
    else:
        abstain = False
        abstain_reason = None

    return PreprocessResult(
        cleaned_text=cleaned_text,
        prose_token_count=prose_tokens,
        abstain=abstain,
        abstain_reason=abstain_reason,
        tamper_alert=tamper_alert,
        tamper_count=tamper_count,
        tamper_details=tamper_details,
        latex_regions_masked=latex_masked,
        citations_masked=citations_masked,
    )
