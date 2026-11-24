import os
import time
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from .content_fetcher import fetch_page_text, compare_snippets, analyze_coherence, verify_web_match
from .shingling import process_text_into_chunks
from .citation_parser import has_citations
from .bibliography_extractor import BibliographyIndex, build_bibliography_index
from .common_knowledge_filter import should_skip_from_web_search

logger = logging.getLogger(__name__)


class SerperClient:
    """Search client with snippets-first approach, primary + backup Serper key rotation, Redis caching, ddgs fallback."""

    def __init__(self, api_key: Optional[str] = None, backup_api_key: Optional[str] = None, bypass_cache: bool = False):
        import redis
        from app.core.config import settings

        self.bypass_cache = bypass_cache or getattr(settings, "DRAGNET_BYPASS_CACHE", False)

        try:
            self.cache = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True
            )
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e}")
            self.cache = None

        redis_key = None
        if self.cache:
            try:
                val = self.cache.get("config:serper_api_key")
                if isinstance(val, str) and val.strip():
                    redis_key = val.strip()
            except Exception:
                pass

        # Primary and backup key resolution
        self.primary_key = (
            api_key
            or os.getenv("SERPER_API_KEY")
            or redis_key
            or getattr(settings, "SERPER_API_KEY", "")
            or ""
        )
        raw_backup = (
            backup_api_key
            or os.getenv("SERPER_BACKUP_KEYS")
            or os.getenv("SERPER_BACKUP_KEY")
            or getattr(settings, "SERPER_BACKUP_KEYS", "")
            or getattr(settings, "SERPER_BACKUP_KEY", "")
            or ""
        )
        if isinstance(raw_backup, str):
            self.backup_keys = [k.strip() for k in raw_backup.split(",") if k.strip()]
        elif isinstance(raw_backup, (list, tuple)):
            self.backup_keys = [k.strip() for k in raw_backup if isinstance(k, str) and k.strip()]
        else:
            self.backup_keys = []

        self.backup_key = self.backup_keys[0] if self.backup_keys else ""
        self.api_key = self.primary_key  # default active

        search_url = os.getenv("SEARCH_ENGINE_URL", "")
        # Auto-detect SerpApi vs Serper.dev
        if "serpapi.com" in search_url.lower() or (self.api_key and "serpapi" in self.api_key.lower()) or os.getenv("SERPAPI_API_KEY"):
            self.engine_type = "serpapi"
            self.endpoint = "https://serpapi.com/search.json"
        else:
            self.engine_type = "serper"
            self.endpoint = "https://google.serper.dev/search"

    def _call_serper(self, query: str, num_results: int, key: str) -> Optional[List[Dict[str, str]]]:
        from app.core.config import settings
        if not key or key in ("", "PASTE_YOUR_KEY_HERE"):
            return None
        try:
            if self.engine_type == "serpapi":
                response = requests.get(
                    self.endpoint,
                    params={"q": query, "num": num_results, "api_key": key, "engine": "google"},
                    timeout=settings.SERPER_TIMEOUT
                )
            else:
                response = requests.post(
                    self.endpoint,
                    headers={'X-API-KEY': key, 'Content-Type': 'application/json'},
                    data=json.dumps({"q": query, "num": num_results}),
                    timeout=settings.SERPER_TIMEOUT
                )
            if response.status_code == 200:
                data = response.json()
                results = []
                items = data.get("organic_results", []) if self.engine_type == "serpapi" else data.get("organic", [])
                for item in items:
                    url = item.get("link", "")
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    if url:
                        results.append({"url": url, "title": title, "snippet": snippet})
                return results
            else:
                logger.warning(f"Serper API key returned status {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            logger.warning(f"{self.engine_type} API failed with key: {e}")
            return None

    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Returns list of {url, snippet, title} dicts with primary + backup rotation and ddgs fallback.
        """
        cache_key = f"serper_snippets:{query}"
        if not self.bypass_cache and self.cache:
            try:
                cached = self.cache.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        results = None
        # Tier 1: Try Primary Key
        if self.primary_key:
            results = self._call_serper(query, num_results, self.primary_key)

        # Tier 2: Try Backup Keys in order if Primary failed or was depleted
        if not results and self.backup_keys:
            for idx, b_key in enumerate(self.backup_keys, 1):
                if b_key and b_key != self.primary_key:
                    logger.info(f"Failing over to backup Serper API key #{idx}...")
                    results = self._call_serper(query, num_results, b_key)
                    if results:
                        break

        # Tier 3: DuckDuckGo fallback
        if not results:
            results = []
            try:
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS
                ddgs = DDGS()
                for r in ddgs.text(query, max_results=num_results) or []:
                    results.append({
                        "url": r.get("href", ""),
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                    })
            except Exception as e:
                logger.warning(f"DuckDuckGo fallback failed: {e}")

        if not self.bypass_cache and self.cache and results:
            try:
                self.cache.setex(cache_key, 86400, json.dumps(results))
            except Exception:
                pass

        return results or []


def _build_matched_char_ranges(internal_matches: List[Dict[str, Any]]) -> List[tuple]:
    """Build sorted list of (char_start, char_end) for all internal matches."""
    ranges = []
    for m in internal_matches:
        start = m.get("submitted_start_char")
        end = m.get("submitted_end_char")
        if start is not None and end is not None and end > start:
            ranges.append((start, end))
    ranges.sort()
    return ranges


def _is_chunk_internally_matched(chunk: Dict[str, Any],
                                  matched_ranges: List[tuple],
                                  overlap_threshold: float = 0.5) -> bool:
    """
    Returns True if this chunk's character range overlaps with any internal match
    by more than overlap_threshold of the chunk's length.
    Implements FR-3.1: skip chunks already caught by internal similarity.
    """
    c_start = chunk.get("char_start", 0)
    c_end = chunk.get("char_end", 0)
    chunk_len = c_end - c_start
    if chunk_len <= 0:
        return False

    for m_start, m_end in matched_ranges:
        overlap = min(c_end, m_end) - max(c_start, m_start)
        if overlap > 0 and (overlap / chunk_len) >= overlap_threshold:
            return True
    return False


def select_suspicious_chunks(text: str,
                              internal_matches: Optional[List[Dict[str, Any]]] = None,
                              page_boundaries: Optional[List[tuple]] = None,
                              page_count: int = 1,
                              max_queries: Optional[int] = None,
                              skip_cited_chunks: bool = True) -> List[Dict[str, Any]]:
    """
    Select chunks suitable for web search:
    - Long enough (>= MIN_CHUNK_WORDS)
    - NOT already internally matched (FR-3.1)
    - NOT already academically cited / referenced (Citation-Aware Guard)
    - Ranked by length; top N selected
    """
    from app.core.config import settings
    if max_queries is None:
        max_queries = settings.MAX_DRAGNET_SUSPICIOUS

    # Filter out self-submissions and excluded matches so prior drafts don't suppress web search
    active_internal_matches = [
        m for m in (internal_matches or [])
        if not m.get("is_self_submission") and not m.get("is_excluded")
    ]
    # Build matched ranges from active internal results for fast overlap check
    matched_ranges = _build_matched_char_ranges(active_internal_matches)

    chunks = process_text_into_chunks(text, page_boundaries=page_boundaries, page_count=page_count)
    suspicious = []

    for c in chunks:
        words = c['text'].split()
        if len(words) < settings.MIN_CHUNK_WORDS:
            continue

        # Skip chunks already caught by internal similarity (FR-3.1)
        if matched_ranges and _is_chunk_internally_matched(c, matched_ranges):
            logger.debug(f"Skipping internally-matched chunk at char {c.get('char_start')}")
            continue

        # Citation-Aware Shield: Skip chunks with in-text academic citations
        if skip_cited_chunks and has_citations(c['text']):
            logger.info(
                f"Web Dragnet Shield: Skipping cited chunk at page {c.get('page', 1)} "
                f"char {c.get('char_start', 0)} (academic citation markers detected)."
            )
            continue

        # Common Domain Knowledge & Polyglot / Math / Boilerplate Filter:
        should_skip, skip_reason = should_skip_from_web_search(c['text'])
        if should_skip:
            logger.info(
                f"Web Dragnet Filter: Skipping chunk at page {c.get('page', 1)} "
                f"char {c.get('char_start', 0)} ({skip_reason})."
            )
            continue

        suspicious.append((len(words), c))

    # Rank by length (longer = better search target)
    suspicious.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in suspicious[:max_queries]]


def run_dragnet(document_id: str,
                text: str,
                internal_matches: Optional[List[Dict[str, Any]]] = None,
                page_boundaries: Optional[List[tuple]] = None,
                page_count: int = 1,
                biblio_index: Optional[BibliographyIndex] = None,
                grobid_references: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Orchestrator for the Web Dragnet Engine.
    - Filters out academically-cited text and common domain knowledge from search dispatch.
    - Grounds search result candidates against document's bibliography (Grobid / text references).
    - Verifies candidate snippets via Two-Stage Hybrid Precision Gate (N-gram verbatim run >= 8 or lexical >= 0.50).
    - Exempts bibliography-grounded sources from plagiarism penalties.
    - Discards commercial / financial homonym collisions.
    - Deduplicates matches by submitted_text so the same chunk doesn't appear multiple times.
    """
    if biblio_index is None:
        biblio_index = build_bibliography_index(grobid_references=grobid_references, full_text=text)

    chunks_to_search = select_suspicious_chunks(
        text,
        internal_matches=internal_matches,
        page_boundaries=page_boundaries,
        page_count=page_count,
        skip_cited_chunks=True
    )

    logger.info(f"Web Dragnet: selected {len(chunks_to_search)} unsourced suspicious chunks "
                f"(after filtering {len(internal_matches or [])} internal matches and cited passages).")

    from app.core.config import settings
    client = SerperClient()

    # submitted_text_hash -> best match dict (dedup by source chunk)
    best_by_chunk: Dict[str, Dict[str, Any]] = {}

    for chunk_dict in chunks_to_search:
        chunk_text = chunk_dict['text']
        chunk_hash = str(hash(chunk_text[:200]))  # stable key for this chunk

        query_words = getattr(settings, 'DRAGNET_QUERY_WORDS', 25)
        query = " ".join(chunk_text.split()[:query_words])
        search_results = client.search(query)
        time.sleep(0.5)  # rate limiting

        for result in search_results:
            url = result.get("url", "")
            snippet = result.get("snippet", "")
            title = result.get("title", "")

            if not url:
                continue

            # Grounding check: is this candidate already documented in the paper's bibliography?
            matched_ref = biblio_index.is_reference_match(
                candidate_url=url,
                candidate_title=title,
                candidate_snippet=snippet
            )
            is_grounded_citation = matched_ref is not None

            # Commercial & Financial Homonym Guard:
            # Reject matches from finance/ecommerce/retail if score is low or homonym collision
            if not is_grounded_citation:
                domain_lower = urlparse(url).netloc.lower()
                commercial_indicators = [
                    "finance.yahoo.com", "amazon.", "ebay.", "walmart.", "aliexpress.",
                    "tripadvisor.", "marketwatch.com", "bloomberg.com/quote", "investing.com"
                ]
                if any(ind in domain_lower for ind in commercial_indicators):
                    logger.debug(f"Web Dragnet: discarding commercial homonym collision: {url}")
                    continue

            # Use snippet directly (avoids robots.txt / JS-heavy pages)
            # Only fetch the full page if the snippet is too short to compare
            source_text = snippet
            if len(snippet.split()) < 20:
                fetched = fetch_page_text(url)
                if fetched:
                    source_text = fetched[:getattr(settings, 'SNIPPET_MAX_CHARS', 2000)]

            if not source_text:
                continue

            # Two-Stage Hybrid Precision Gate (Verbatim N-gram Run >= 8 or Lexical Ratio >= 0.50 or Paraphrase >= 0.70)
            verification = verify_web_match(chunk_text, source_text)
            if not verification["is_match"] and not is_grounded_citation:
                logger.debug(
                    f"Web Dragnet: Candidate rejected for {url} -> {verification['rejection_reason']}"
                )
                continue

            score = verification["score"]
            web_threshold = getattr(settings, 'WEB_MATCH_THRESHOLD', 0.50)

            if score >= web_threshold or is_grounded_citation:
                domain = urlparse(url).netloc

                # Grounded reference configuration:
                # If the source is in the document's references, exclude from plagiarism penalty
                is_excluded = is_grounded_citation
                exclude_reason = f"Documented in References ({matched_ref.label})" if is_grounded_citation else None
                source_display_title = (
                    f"[Attributed] {matched_ref.title or title or domain}"
                    if is_grounded_citation else (title or domain)
                )

                if is_grounded_citation:
                    logger.info(
                        f"Web Dragnet: Citation Grounded match found for {url} -> "
                        f"Matches Reference {matched_ref.label}. Excluded from plagiarism penalty."
                    )

                match = {
                    "type": "web",
                    "url": url,
                    "domain": domain,
                    "score": score,
                    "source_title": source_display_title,
                    "source_text": source_text[:getattr(settings, 'SNIPPET_MAX_CHARS', 2000)],
                    "submitted_text": chunk_text,
                    "similarity_score": round(score * 100, 2),
                    "submitted_page": chunk_dict.get("page", 1),
                    "source_page": 1,
                    "submitted_start_char": chunk_dict.get("char_start", 0),
                    "submitted_end_char": chunk_dict.get("char_end", 0),
                    "is_coherent": False,
                    "is_citation_grounded": is_grounded_citation,
                    "is_excluded": is_excluded,
                    "exclude_reason": exclude_reason,
                    "citation_label": matched_ref.label if matched_ref else None,
                    "match_type": verification.get("match_type", "web"),
                    "verbatim_run": verification.get("verbatim_run", 0),
                }

                # Keep only the highest-scoring web match per submitted chunk
                existing = best_by_chunk.get(chunk_hash)
                if existing is None or score > existing["score"]:
                    best_by_chunk[chunk_hash] = match
                    logger.debug(f"Web match: chunk@{chunk_dict.get('page')} → {url} ({score:.2f})")

    matches = list(best_by_chunk.values())
    matches = analyze_coherence(matches)

    logger.info(f"Web Dragnet: {len(matches)} unique web matches found.")
    return matches

