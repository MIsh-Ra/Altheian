"""Centralized academic glossary and plain-English terminology for Alethian audit reports.

This module replaces legacy internal jargon ("Web Dragnet", "Binoculars Ratio",
"DNA Detect Burstiness") with standardized, academic-integrity terms aligned
with university honor boards and institutional repositories.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


# ── Standardized Academic Terminology Constants ──────────────────────────────
INTERNET_SOURCES: str = "Internet & Online Sources"
INSTITUTIONAL_REPOSITORY: str = "Institutional Repository"
IDENTICAL_MATCH: str = "Identical Match (Verbatim)"
PARAPHRASED_MATCH: str = "Paraphrased / Modified Match"
AUTHOR_PREVIOUS_DRAFTS: str = "Author's Previous Drafts (Exempted)"
PROPERLY_CITED_SOURCE: str = "Properly Cited Source (Exempted)"
WORD_CHOICE_PREDICTABILITY: str = "Word Choice Predictability Index"
SENTENCE_RHYTHM_VARIETY: str = "Sentence Rhythm & Structural Variety"
TEMPLATE_EXEMPTED: str = "Institutional Certificate Template (Exempted)"


# ── In-Situ Annotation Color Key (PyMuPDF RGB 0.0 - 1.0) ────────────────────
RGB_AI_LOW: Tuple[float, float, float] = (0.55, 0.85, 0.95)       # Soft cyan/teal (AI prob 0.30 - 0.50)
RGB_AI_MEDIUM: Tuple[float, float, float] = (0.25, 0.75, 0.95)    # Medium cyan (AI prob 0.50 - 0.70)
RGB_AI_HIGH: Tuple[float, float, float] = (0.05, 0.65, 0.95)      # Vibrant cyan (AI prob 0.70 - 1.00)
RGB_VERBATIM: Tuple[float, float, float] = (0.90, 0.20, 0.20)     # Red for identical verbatim matches
RGB_PARAPHRASE: Tuple[float, float, float] = (0.95, 0.45, 0.10)   # Orange for paraphrased/modified matches
RGB_CITED: Tuple[float, float, float] = (0.10, 0.70, 0.30)        # Green for properly cited scholarship
RGB_BOILERPLATE: Tuple[float, float, float] = (0.80, 0.80, 0.80)  # Neutral grey for institutional templates


# ── Hex Colors for ReportLab & Web UI ───────────────────────────────────────
HEX_AI_LOW: str = "#8dd9f2"
HEX_AI_MEDIUM: str = "#40bfe0"
HEX_AI_HIGH: str = "#0da6f2"
HEX_VERBATIM: str = "#e63333"
HEX_PARAPHRASE: str = "#f2731a"
HEX_CITED: str = "#1ab34d"
HEX_BOILERPLATE: str = "#cccccc"


@dataclass(frozen=True)
class AcademicTermDefinition:
    key: str
    display_title: str
    legacy_term: str
    definition: str
    guidance_for_faculty: str


GLOSSARY: Dict[str, AcademicTermDefinition] = {
    "internet_sources": AcademicTermDefinition(
        key="internet_sources",
        display_title=INTERNET_SOURCES,
        legacy_term="Web Dragnet",
        definition="Publicly accessible scholarly and web archives indexed through real-time academic discovery gateways.",
        guidance_for_faculty="Review matched URLs to verify context, open access status, and whether content is general knowledge or subject-specific research."
    ),
    "institutional_repository": AcademicTermDefinition(
        key="institutional_repository",
        display_title=INSTITUTIONAL_REPOSITORY,
        legacy_term="University Institutional Theses",
        definition="The university's internal corpus of theses, dissertations, and past student coursework submissions.",
        guidance_for_faculty="Check for cohort collision or authorized re-use of laboratory datasets between collaborating researchers."
    ),
    "identical_match": AcademicTermDefinition(
        key="identical_match",
        display_title=IDENTICAL_MATCH,
        legacy_term="Exact Match",
        definition="Word-for-word string match where consecutive phrasing mirrors an indexed source without alteration.",
        guidance_for_faculty="Requires quotation marks and formal bibliographic citation if intentional."
    ),
    "paraphrased_match": AcademicTermDefinition(
        key="paraphrased_match",
        display_title=PARAPHRASED_MATCH,
        legacy_term="Paraphrase",
        definition="Semantic or structural equivalence where vocabulary is altered but argument, clause logic, and sentence framework replicate an existing work.",
        guidance_for_faculty="Requires proper attribution to the original author even when expressed in student's own words."
    ),
    "author_previous_drafts": AcademicTermDefinition(
        key="author_previous_drafts",
        display_title=AUTHOR_PREVIOUS_DRAFTS,
        legacy_term="Self-Plagiarism Match",
        definition="Overlap with earlier drafts or milestone submissions submitted by the same author.",
        guidance_for_faculty="Exempted from plagiarism scoring under iterative drafting protocols."
    ),
    "properly_cited_source": AcademicTermDefinition(
        key="properly_cited_source",
        display_title=PROPERLY_CITED_SOURCE,
        legacy_term="Citation Match",
        definition="Passages that match external literature but are accompanied by standard academic in-text citations and reference list entries.",
        guidance_for_faculty="Legitimate scholarly attribution. Exempted from originality penalties."
    ),
    "word_choice_predictability": AcademicTermDefinition(
        key="word_choice_predictability",
        display_title=WORD_CHOICE_PREDICTABILITY,
        legacy_term="Binoculars Perplexity Ratio",
        definition="Statistical evaluation of how predictably words succeed each other compared to baseline human author distributions.",
        guidance_for_faculty="Consistently elevated predictability across multiple paragraphs suggests automated text synthesis."
    ),
    "sentence_rhythm_variety": AcademicTermDefinition(
        key="sentence_rhythm_variety",
        display_title=SENTENCE_RHYTHM_VARIETY,
        legacy_term="DNA-Detect Burstiness Score",
        definition="Quantification of syntactic variety, sentence length alternation, and rhetorical pacing.",
        guidance_for_faculty="Human academic writing exhibits high variance in sentence structure; uniform pacing suggests LLM generation."
    ),
    "boilerplate_exempted": AcademicTermDefinition(
        key="boilerplate_exempted",
        display_title=TEMPLATE_EXEMPTED,
        legacy_term="Institutional Template Match",
        definition="Standardized departmental certificates of bonafide work, student declarations, and institutional cover formulas.",
        guidance_for_faculty="Zero penalty recommended; standard institutional requirement."
    ),
}


def map_legacy_source_type(source_type: str) -> str:
    """Map internal database source types to plain-English academic terms."""
    st = (source_type or "").lower().strip()
    if st in ("web", "web_dragnet", "internet"):
        return INTERNET_SOURCES
    if st in ("internal", "archive", "thesis", "theses"):
        return INSTITUTIONAL_REPOSITORY
    return INTERNET_SOURCES


def map_legacy_match_type(match_type: str, is_excluded: bool = False, exclude_reason: str = "") -> str:
    """Map internal match types to plain-English academic terms."""
    if is_excluded:
        reason_lower = (exclude_reason or "").lower()
        if "reference" in reason_lower or "citation" in reason_lower:
            return PROPERLY_CITED_SOURCE
        if "draft" in reason_lower or "prior submission" in reason_lower:
            return AUTHOR_PREVIOUS_DRAFTS
        if "template" in reason_lower or "bonafide" in reason_lower:
            return TEMPLATE_EXEMPTED
    mt = (match_type or "").lower().strip()
    if mt in ("internal_exact", "exact", "identical"):
        return IDENTICAL_MATCH
    if mt in ("internal_paraphrase", "paraphrase", "modified"):
        return PARAPHRASED_MATCH
    return IDENTICAL_MATCH
