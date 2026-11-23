"""
Academic Citation Parser Engine for Alethian v3.1.
Detects in-text academic citations across four standard families:
1. Numerical bracketed: [1], [12, 14], [1-5], [18]
2. Author-year parenthetical: (Smith et al., 2024), (Liang et al., 2023)
3. Superscripts & caret notations: ^9, ^60, derivations60, ¹, ², ³
4. Attributive lead-in phrases: "In Liang et al.'s landmark Patterns (2023) study", "According to Hans et al."
"""
import re
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

CitationType = Literal["bracketed", "author_year", "superscript", "attributive"]


class CitationMarker(BaseModel):
    marker_type: CitationType
    raw_token: str
    citation_keys: List[str] = Field(default_factory=list)
    char_start: int
    char_end: int


class ChunkCitationProfile(BaseModel):
    chunk_index: int = 0
    text: str
    is_cited: bool = False
    markers: List[CitationMarker] = Field(default_factory=list)
    citation_density: float = 0.0  # markers per 100 words


# ── REGEX PATTERNS ─────────────────────────────────────────────────────────────

# 1. Bracketed numerical citations: [1], [1, 2], [1-5], [12, 14], [12, 14, 18]
RE_BRACKETED = re.compile(
    r'\[\s*(\d{1,3}(?:\s*[-–,]\s*\d{1,3})*)\s*\]'
)

# 2. Author-Year parentheticals: (Smith et al., 2024), (Liang et al., 2023; Hans et al., 2024)
RE_AUTHOR_YEAR = re.compile(
    r'\(\s*([A-Z][a-zA-Z\s.-]+(?:\s+et\s+al\.)?,\s*(?:19|20)\d{2}[a-z]?'
    r'(?:\s*;\s*[A-Z][a-zA-Z\s.-]+(?:\s+et\s+al\.)?,\s*(?:19|20)\d{2}[a-z]?)*)\s*\)'
)

# 3. Superscripts and Carets: ^9, ^60, derivations^60, AUROC^9, or standalone trailing numbers like "proofs 60"
# Also unicode superscripts: ¹, ², ³, ⁴, ⁵, ⁶, ⁷, ⁸, ⁹, ⁰
RE_UNICODE_SUPERSCRIPT = re.compile(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]+')
RE_CARET_SUPERSCRIPT = re.compile(r'\^(\d{1,3})\b')
# OCR artifacts where superscript became attached number after punctuation or word: "AUROC 9 .", "derivations 60 ."
RE_ATTACHED_SUPERSCRIPT = re.compile(r'(?<=[a-zA-Z,;:)\"\'`])[\^]?(\d{1,3})(?=\s*[,.;:)]|\s+[A-Z])')

# 4. Attributive lead-in phrases with author and year/study:
# "In Liang et al.’s landmark Patterns (2023) study"
# "According to Hans et al. (2024)"
# "Fast-DetectGPT's authors updated their repository"
RE_ATTRIBUTIVE_LEADIN = re.compile(
    r'\b(?:According\s+to|In|As\s+shown\s+by|As\s+demonstrated\s+by|As\s+noted\s+in|study\s+by)\s+'
    r'([A-Z][a-zA-Z\s.-]+(?:\s+et\s+al\.)?)\s*'
    r"(?:[’']s|\s*\((?:19|20)\d{2}\)|\s+landmark|\s+study|\s+paper|\s+authors|\s+findings)",
    re.IGNORECASE
)

# Specific author-tool attribution: "Fast-DetectGPT's authors", "Binoculars authors", "TII achieved"
RE_AUTHOR_TOOL = re.compile(
    r'\b([A-Z][a-zA-Z0-9_-]+(?:-[A-Z][a-zA-Z0-9_-]+)*)'
    r"(?:[’']s\s+authors|[’']s\s+repository|[’']s\s+team|[’']s\s+audit)\b",
    re.IGNORECASE
)


def _convert_unicode_superscripts(text: str) -> str:
    sup_map = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
    return text.translate(sup_map)


def parse_citations_in_chunk(text: str, chunk_index: int = 0) -> ChunkCitationProfile:
    """
    Scans a chunk of text for in-text citations.
    Returns a ChunkCitationProfile detailing all identified markers and whether
    the chunk is classified as academically cited / sourced.
    """
    if not text or not text.strip():
        return ChunkCitationProfile(chunk_index=chunk_index, text=text or "", is_cited=False)

    markers: List[CitationMarker] = []
    seen_spans = set()

    # 1. Bracketed numerical citations
    for match in RE_BRACKETED.finditer(text):
        span = match.span()
        if span in seen_spans:
            continue
        raw_inside = match.group(1)
        # Parse individual numbers or ranges e.g. "12, 14" -> ["12", "14"], "1-3" -> ["1", "2", "3"]
        keys = []
        for part in re.split(r'[,;]', raw_inside):
            part = part.strip()
            if '-' in part or '–' in part:
                range_parts = re.split(r'[-–]', part)
                if len(range_parts) == 2 and range_parts[0].strip().isdigit() and range_parts[1].strip().isdigit():
                    start_num = int(range_parts[0].strip())
                    end_num = int(range_parts[1].strip())
                    if 0 < end_num - start_num <= 20:
                        keys.extend(str(n) for n in range(start_num, end_num + 1))
                        continue
            if part.isdigit():
                keys.append(part)

        if keys:
            seen_spans.add(span)
            markers.append(CitationMarker(
                marker_type="bracketed",
                raw_token=match.group(0),
                citation_keys=keys,
                char_start=span[0],
                char_end=span[1]
            ))

    # 2. Author-Year parentheticals
    for match in RE_AUTHOR_YEAR.finditer(text):
        span = match.span()
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
            continue
        raw_inside = match.group(1).strip()
        keys = [k.strip() for k in raw_inside.split(";") if k.strip()]
        if keys:
            seen_spans.add(span)
            markers.append(CitationMarker(
                marker_type="author_year",
                raw_token=match.group(0),
                citation_keys=keys,
                char_start=span[0],
                char_end=span[1]
            ))

    # 3. Unicode Superscripts
    for match in RE_UNICODE_SUPERSCRIPT.finditer(text):
        span = match.span()
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
            continue
        converted = _convert_unicode_superscripts(match.group(0))
        if converted.isdigit():
            seen_spans.add(span)
            markers.append(CitationMarker(
                marker_type="superscript",
                raw_token=match.group(0),
                citation_keys=[converted],
                char_start=span[0],
                char_end=span[1]
            ))

    # 3b. Caret & Attached Superscripts (e.g. ^9, derivations^60)
    for match in RE_CARET_SUPERSCRIPT.finditer(text):
        span = match.span()
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
            continue
        num = match.group(1)
        seen_spans.add(span)
        markers.append(CitationMarker(
            marker_type="superscript",
            raw_token=match.group(0),
            citation_keys=[num],
            char_start=span[0],
            char_end=span[1]
        ))

    for match in RE_ATTACHED_SUPERSCRIPT.finditer(text):
        span = match.span()
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
            continue
        num = match.group(1)
        # Avoid common standalone numbers or page counts: only accept if plausible reference (1-500)
        if 1 <= int(num) <= 500:
            seen_spans.add(span)
            markers.append(CitationMarker(
                marker_type="superscript",
                raw_token=match.group(0),
                citation_keys=[num],
                char_start=span[0],
                char_end=span[1]
            ))

    # 4. Attributive Lead-ins and Tool Authors
    for match in RE_ATTRIBUTIVE_LEADIN.finditer(text):
        span = match.span()
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
            continue
        author = match.group(1).strip()
        seen_spans.add(span)
        markers.append(CitationMarker(
            marker_type="attributive",
            raw_token=match.group(0),
            citation_keys=[author],
            char_start=span[0],
            char_end=span[1]
        ))

    for match in RE_AUTHOR_TOOL.finditer(text):
        span = match.span()
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
            continue
        tool = match.group(1).strip()
        seen_spans.add(span)
        markers.append(CitationMarker(
            marker_type="attributive",
            raw_token=match.group(0),
            citation_keys=[tool],
            char_start=span[0],
            char_end=span[1]
        ))

    words = len(text.split())
    density = (len(markers) / max(words, 1)) * 100.0
    is_cited = len(markers) > 0

    return ChunkCitationProfile(
        chunk_index=chunk_index,
        text=text,
        is_cited=is_cited,
        markers=markers,
        citation_density=round(density, 2)
    )


def has_citations(text: str) -> bool:
    """Fast-path predicate returning True if chunk contains any academic citation markers."""
    if not text or len(text.strip()) < 20:
        return False
    # Quick check for common markers before executing full regex scanner
    if ('[' in text and ']' in text) or ('(' in text and ')' in text) or ('^' in text) or ('et al' in text.lower()):
        profile = parse_citations_in_chunk(text)
        return profile.is_cited
    # Fallback to check attached superscripts or attributive lead-ins
    profile = parse_citations_in_chunk(text)
    return profile.is_cited
