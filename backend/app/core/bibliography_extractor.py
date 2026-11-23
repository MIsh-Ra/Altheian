"""
Bibliography and Reference Extraction & Grounding Engine for Alethian v3.1.

Extracts formal bibliography items from:
1. Grobid XML structured <listBibl> records
2. Raw document text fallback (References / Bibliography / Works Cited terminal sections)

Builds a high-performance BibliographyIndex supporting:
- Exact & canonical URL matching (normalizing http/https, trailing slashes, .pdf extensions)
- DOI resolution and matching
- Fuzzy academic title token overlap matching
- Fast citation grounding predicate for Web Dragnet filtering
"""
import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Standard Regexes for Reference Parsing
RE_URL = re.compile(r'https?://[^\s<>"\')]+', re.IGNORECASE)
RE_DOI = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b', re.IGNORECASE)
RE_ARXIV = re.compile(r'(?:arxiv:\s*|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5}(?:v\d+)?)', re.IGNORECASE)
RE_YEAR = re.compile(r'\b(19\d{2}|20\d{2})\b')

# Terminal reference section header regex
RE_BIBLIO_SECTION = re.compile(
    r'(?:\n|\A)\s*(?:[#=*-]+\s*)?(?:REFERENCES|BIBLIOGRAPHY|WORKS\s+CITED|LITERATURE\s+CITED)\s*(?:[#=*-]+)?\s*(?:\n|\Z)',
    re.IGNORECASE
)

# Individual reference line starter
RE_REF_START_NUM = re.compile(r'^(?:\[(\d{1,3})\]|(\d{1,3})\.|\b(\d{1,3})\s+)\s*')
RE_REF_START_AUTHOR = re.compile(r'^[A-Z][a-zA-Z\s.-]+,\s*[A-Z]')

# Minimal stop words for academic title token matching
STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by", "from",
    "of", "as", "is", "are", "was", "were", "be", "been", "that", "this", "these", "those",
    "using", "via", "towards", "based", "approach", "framework", "study", "analysis"
}


class ReferenceEntry(BaseModel):
    index: int
    label: str  # e.g. "[26]", "Ref #26", "Hans et al. (2024)"
    raw_text: str
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    urls: List[str] = Field(default_factory=list)
    dois: List[str] = Field(default_factory=list)
    arxiv_ids: List[str] = Field(default_factory=list)


def normalize_url(url: str) -> str:
    """Canonicalize URL for deterministic lookup."""
    if not url:
        return ""
    url = url.strip().rstrip(".,;)\"'>")
    # Lowercase scheme and domain
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/")
    if path.endswith(".pdf"):
        path = path[:-4]
    return f"{netloc}{path}"


def normalize_doi(doi: str) -> str:
    """Canonicalize DOI."""
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', doi)
    return doi.rstrip(".,;)")


def tokenize_title(title: str) -> Set[str]:
    """Tokenize and filter substantive alphanumeric terms from academic titles."""
    if not title:
        return set()
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', title.lower())
    tokens = {t for t in cleaned.split() if len(t) >= 3 and t not in STOP_WORDS}
    return tokens


class BibliographyIndex:
    """Index of document references providing O(1) URL/DOI lookups and fuzzy title matching."""

    def __init__(self, entries: List[ReferenceEntry]):
        self.entries = entries
        self.url_map: Dict[str, ReferenceEntry] = {}
        self.doi_map: Dict[str, ReferenceEntry] = {}
        self.arxiv_map: Dict[str, ReferenceEntry] = {}
        self.title_tokens: List[Tuple[Set[str], ReferenceEntry]] = []

        for entry in self.entries:
            for u in entry.urls:
                norm_u = normalize_url(u)
                if norm_u:
                    self.url_map[norm_u] = entry
                    # Also map prefix domain + main path id (e.g. aclanthology.org/2026.acl-long.1748)
                    parts = norm_u.split("/")
                    if len(parts) >= 2:
                        self.url_map["/".join(parts[:2])] = entry

            for d in entry.dois:
                norm_d = normalize_doi(d)
                if norm_d:
                    self.doi_map[norm_d] = entry

            for arx in entry.arxiv_ids:
                cleaned_arx = arx.lower().strip()
                self.arxiv_map[cleaned_arx] = entry

            # Collect substantive tokens from title and raw text
            ref_tokens = tokenize_title(entry.title) if entry.title else set()
            raw_tokens = tokenize_title(entry.raw_text)
            combined_tokens = ref_tokens | raw_tokens
            if len(combined_tokens) >= 2:
                self.title_tokens.append((combined_tokens, entry))

    def matches_url(self, candidate_url: str) -> Optional[ReferenceEntry]:
        """Check if a candidate URL matches any cited reference."""
        if not candidate_url or not self.url_map:
            return None
        norm_candidate = normalize_url(candidate_url)
        if norm_candidate in self.url_map:
            return self.url_map[norm_candidate]

        # Check prefix matching
        parts = norm_candidate.split("/")
        if len(parts) >= 2:
            prefix = "/".join(parts[:2])
            if prefix in self.url_map:
                return self.url_map[prefix]

        return None

    def matches_doi(self, candidate_doi: str) -> Optional[ReferenceEntry]:
        """Check if candidate DOI matches any cited reference."""
        if not candidate_doi or not self.doi_map:
            return None
        norm_d = normalize_doi(candidate_doi)
        return self.doi_map.get(norm_d)

    def matches_arxiv(self, text: str) -> Optional[ReferenceEntry]:
        """Check if candidate text contains a cited arXiv ID."""
        if not text or not self.arxiv_map:
            return None
        for match in RE_ARXIV.finditer(text):
            aid = match.group(1).lower()
            if aid in self.arxiv_map:
                return self.arxiv_map[aid]
        return None

    def matches_title_fuzzy(self, candidate_title: str, threshold: float = 0.60) -> Optional[ReferenceEntry]:
        """
        Check if candidate title has strong token overlap with any reference title.
        Requires Jaccard overlap >= threshold and at least 3 matching informative tokens.
        """
        if not candidate_title or not self.title_tokens:
            return None

        c_tokens = tokenize_title(candidate_title)
        if len(c_tokens) < 3:
            return None

        best_entry = None
        best_overlap = 0.0

        for r_tokens, entry in self.title_tokens:
            intersection = len(c_tokens & r_tokens)
            if intersection < 3:
                continue
            union = len(c_tokens | r_tokens)
            jaccard = intersection / max(union, 1)

            # Also check subset containment if candidate title is long
            coverage = intersection / len(r_tokens)
            score = max(jaccard, coverage * 0.85)

            if score >= threshold and score > best_overlap:
                best_overlap = score
                best_entry = entry

        return best_entry

    def is_reference_match(
        self,
        candidate_url: str,
        candidate_title: str = "",
        candidate_snippet: str = ""
    ) -> Optional[ReferenceEntry]:
        """
        Master matching predicate: checks URL, DOI, arXiv, and title similarity.
        Returns matching ReferenceEntry if grounded, or None.
        """
        # 1. URL direct match
        match = self.matches_url(candidate_url)
        if match:
            return match

        # 2. Extract DOI from URL or snippet
        text_to_search = f"{candidate_url} {candidate_title} {candidate_snippet}"
        for doi_match in RE_DOI.finditer(text_to_search):
            match = self.matches_doi(doi_match.group(0))
            if match:
                return match

        # 3. Check arXiv ID
        match = self.matches_arxiv(text_to_search)
        if match:
            return match

        # 4. Title overlap
        if candidate_title:
            match = self.matches_title_fuzzy(candidate_title, threshold=0.58)
            if match:
                return match

        return None


def extract_bibliography_from_grobid(grobid_references: List[Dict[str, Any]]) -> List[ReferenceEntry]:
    """Parse Grobid structured references into ReferenceEntry objects."""
    entries: List[ReferenceEntry] = []
    if not grobid_references:
        return entries

    for i, item in enumerate(grobid_references):
        raw = item.get("raw", "").strip()
        title = item.get("title")
        if title in ["Unknown Reference", ""]:
            title = None

        urls = RE_URL.findall(raw)
        dois = RE_DOI.findall(raw)
        arxiv_ids = [m.group(1) for m in RE_ARXIV.finditer(raw)]

        year_match = RE_YEAR.search(raw)
        year = int(year_match.group(1)) if year_match else None

        entries.append(ReferenceEntry(
            index=i + 1,
            label=f"[{i + 1}]",
            raw_text=raw,
            title=title,
            year=year,
            urls=urls,
            dois=dois,
            arxiv_ids=arxiv_ids
        ))
    return entries


def extract_bibliography_from_text(full_text: str) -> List[ReferenceEntry]:
    """
    Regex-based fallback extraction parsing terminal 'References' or 'Works Cited' sections.
    Handles bracketed numbers [1], numbered items 1., and author-year blocks.
    """
    entries: List[ReferenceEntry] = []
    if not full_text:
        return entries

    # Find the last occurrence of references header
    matches = list(RE_BIBLIO_SECTION.finditer(full_text))
    if not matches:
        return entries

    # Take the last section header
    last_header = matches[-1]
    biblio_text = full_text[last_header.end():].strip()
    if len(biblio_text) < 50:
        return entries

    # Split into lines/paragraphs
    raw_lines = biblio_text.split("\n")
    current_entry_lines = []
    current_index = 1
    current_label = f"[{current_index}]"

    def flush_entry():
        nonlocal current_entry_lines, current_index, current_label
        if not current_entry_lines:
            return
        entry_text = " ".join(current_entry_lines).strip()
        if len(entry_text) >= 15:
            urls = RE_URL.findall(entry_text)
            dois = RE_DOI.findall(entry_text)
            arxiv_ids = [m.group(1) for m in RE_ARXIV.finditer(entry_text)]
            year_match = RE_YEAR.search(entry_text)
            year = int(year_match.group(1)) if year_match else None

            # Attempt title heuristic: text in quotes or between author and venue
            title = None
            quote_match = re.search(r'["“](.+?)["”]', entry_text)
            if quote_match and len(quote_match.group(1).split()) >= 3:
                title = quote_match.group(1).strip()
            elif "." in entry_text:
                parts = entry_text.split(".")
                for p in parts:
                    p = p.strip()
                    if len(p.split()) >= 3 and not RE_URL.search(p) and not RE_DOI.search(p):
                        title = p
                        break
            if not title and len(entry_text.split()) >= 3:
                title = entry_text.strip()

            entries.append(ReferenceEntry(
                index=current_index,
                label=current_label,
                raw_text=entry_text,
                title=title,
                year=year,
                urls=urls,
                dois=dois,
                arxiv_ids=arxiv_ids
            ))
            current_index += 1
            current_label = f"[{current_index}]"
        current_entry_lines = []

    for line in raw_lines:
        line_str = line.strip()
        if not line_str:
            continue

        num_match = RE_REF_START_NUM.match(line_str)
        if num_match:
            flush_entry()
            num_val = num_match.group(1) or num_match.group(2) or num_match.group(3)
            if num_val:
                current_label = f"[{num_val}]"
            current_entry_lines.append(RE_REF_START_NUM.sub('', line_str))
        else:
            # Check if this line looks like a fresh author-year entry
            if not current_entry_lines:
                current_entry_lines.append(line_str)
            else:
                # If current entry already has substantial length and line starts with Author capitalized
                if len(" ".join(current_entry_lines)) > 100 and RE_REF_START_AUTHOR.match(line_str):
                    flush_entry()
                    current_entry_lines.append(line_str)
                else:
                    current_entry_lines.append(line_str)

    flush_entry()
    return entries


def build_bibliography_index(
    grobid_references: Optional[List[Dict[str, Any]]] = None,
    full_text: Optional[str] = None
) -> BibliographyIndex:
    """
    Constructs a unified BibliographyIndex. Prioritizes Grobid structured data
    and enriches with regex text fallback if Grobid extracted few or no entries.
    """
    entries: List[ReferenceEntry] = []
    if grobid_references and len(grobid_references) > 0:
        entries = extract_bibliography_from_grobid(grobid_references)

    # If Grobid found very few references (< 3) but document is long, try text fallback
    if len(entries) < 3 and full_text:
        text_entries = extract_bibliography_from_text(full_text)
        if len(text_entries) > len(entries):
            logger.info(f"Using text fallback bibliography: found {len(text_entries)} references.")
            entries = text_entries

    logger.info(f"Constructed BibliographyIndex with {len(entries)} references.")
    return BibliographyIndex(entries)
