import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import util as st_util
except ImportError:
    st_util = None
from app.core.embeddings import get_model

def fetch_page_text(url, timeout=None):
    """Fetches and cleans HTML from a URL, with robots.txt check and timeout."""
    from app.core.config import settings
    if timeout is None:
        timeout = settings.FETCHER_TIMEOUT
    headers = {'User-Agent': 'Alethian-Search-Bot/1.0'}
    try:
        from urllib.robotparser import RobotFileParser
        
        parsed_url = urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            if not rp.can_fetch(headers['User-Agent'], url):
                logger.info(f"Blocked by robots.txt: {url}")
                return ""
        except Exception as e:
            pass # Ignore robots parser failure

        response = requests.get(url, headers=headers, timeout=timeout)
        if "application/pdf" in response.headers.get('Content-Type', ''):
            return ""
        soup = BeautifulSoup(response.content, 'html.parser')
        # Cleanup
        for junk in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            junk.extract()
        text = soup.get_text()
        return '\n'.join(chunk for line in text.splitlines() for chunk in [line.strip()] if chunk)
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return ""

import difflib
import re

def calculate_longest_verbatim_run(text1: str, text2: str) -> int:
    """Computes the length of the longest continuous sequence of matching words."""
    w1 = [re.sub(r'[^a-zA-Z0-9]', '', w.lower()) for w in text1.split() if re.sub(r'[^a-zA-Z0-9]', '', w.lower())]
    w2 = [re.sub(r'[^a-zA-Z0-9]', '', w.lower()) for w in text2.split() if re.sub(r'[^a-zA-Z0-9]', '', w.lower())]
    if not w1 or not w2:
        return 0
    sm = difflib.SequenceMatcher(None, w1, w2)
    match = sm.find_longest_match(0, len(w1), 0, len(w2))
    return match.size


def calculate_token_jaccard(text1: str, text2: str) -> float:
    """Computes token Jaccard similarity between non-stopwords."""
    stop_words = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by", "is", "was", "are", "were", "it", "this", "that"}
    t1 = set(re.sub(r'[^a-zA-Z0-9]', '', w.lower()) for w in text1.split()) - stop_words - {""}
    t2 = set(re.sub(r'[^a-zA-Z0-9]', '', w.lower()) for w in text2.split()) - stop_words - {""}
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)


def compare_snippets_cosine(submitted_text: str, source_text: str) -> float:
    """Compare a submitted chunk against windows in source text via embedding cosine similarity."""
    _model = get_model()
    if not submitted_text or not source_text or _model is None:
        return 0.0
    try:
        from app.core.config import settings
        from app.core.embeddings import generate_embeddings_batch
        emb1 = _model.encode(submitted_text, convert_to_tensor=True)
        
        if len(source_text) < settings.MIN_SOURCE_TEXT_LENGTH: 
            return 0.0
        
        source_words = source_text.split()
        window_size = settings.FETCHER_WINDOW_SIZE
        step = settings.FETCHER_WINDOW_STEP
        
        if len(source_words) <= window_size:
            emb2 = _model.encode(source_text, convert_to_tensor=True)
            return max(0.0, st_util.cos_sim(emb1, emb2).item())
        
        windows = []
        for i in range(0, len(source_words) - window_size + 1, step):
            windows.append(" ".join(source_words[i:i + window_size]))

        if not windows:
            return 0.0
            
        batch_embs = generate_embeddings_batch(windows)
        best_score = 0.0
        for emb2_list in batch_embs:
            import torch
            emb2 = torch.tensor(emb2_list)
            score = st_util.cos_sim(emb1, emb2).item()
            if score > best_score:
                best_score = score
        
        return max(0.0, best_score)
    except Exception as e:
        logger.error(f"Error computing cosine similarity: {e}")
        return 0.0


def verify_web_match(submitted_text: str, source_text: str) -> dict:
    """
    Two-Stage Hybrid Precision Gate:
    Validates candidate matches against verbatim runs, lexical overlap, and dense semantic paraphrase.
    Rejects topical co-occurrence (common domain knowledge).
    """
    from app.core.config import settings
    verbatim_run = calculate_longest_verbatim_run(submitted_text, source_text)
    lexical_ratio = difflib.SequenceMatcher(None, submitted_text.lower(), source_text.lower()).ratio()
    cosine_sim = compare_snippets_cosine(submitted_text, source_text)
    jaccard = calculate_token_jaccard(submitted_text, source_text)

    min_verbatim = getattr(settings, "MIN_VERBATIM_RUN_WORDS", 8)
    min_lexical = getattr(settings, "WEB_LEXICAL_RATIO_THRESHOLD", 0.50)
    min_semantic = getattr(settings, "WEB_SEMANTIC_PARAPHRASE_THRESHOLD", 0.70)

    # Criterion 1: Verbatim Run >= min_verbatim
    if verbatim_run >= min_verbatim:
        effective_score = max(lexical_ratio, min(1.0, verbatim_run / 20.0), cosine_sim)
        return {
            "is_match": True,
            "score": effective_score,
            "match_type": "verbatim_run",
            "verbatim_run": verbatim_run,
            "lexical_ratio": lexical_ratio,
            "cosine_similarity": cosine_sim,
            "rejection_reason": None,
        }

    # Criterion 2: Substantial Lexical Overlap >= min_lexical
    if lexical_ratio >= min_lexical:
        return {
            "is_match": True,
            "score": max(lexical_ratio, cosine_sim),
            "match_type": "lexical_alignment",
            "verbatim_run": verbatim_run,
            "lexical_ratio": lexical_ratio,
            "cosine_similarity": cosine_sim,
            "rejection_reason": None,
        }

    # Criterion 3: Dense Semantic Paraphrase (Cosine >= 0.70 AND Token Jaccard >= 0.35)
    if cosine_sim >= min_semantic and jaccard >= 0.35:
        return {
            "is_match": True,
            "score": cosine_sim,
            "match_type": "semantic_paraphrase",
            "verbatim_run": verbatim_run,
            "lexical_ratio": lexical_ratio,
            "cosine_similarity": cosine_sim,
            "rejection_reason": None,
        }

    # Rejected: Topical co-occurrence without lexical identity (Common Domain Knowledge)
    return {
        "is_match": False,
        "score": 0.0,
        "match_type": "topical_coincidence",
        "verbatim_run": verbatim_run,
        "lexical_ratio": lexical_ratio,
        "cosine_similarity": cosine_sim,
        "rejection_reason": (
            f"Common domain knowledge / topical co-occurrence "
            f"(verbatim run: {verbatim_run} words < {min_verbatim}, "
            f"lexical ratio: {lexical_ratio:.2f} < {min_lexical}, "
            f"cosine: {cosine_sim:.2f})"
        ),
    }


def compare_snippets(submitted_text: str, source_text: str) -> float:
    """Backward-compatible entry point returning hybrid verified score."""
    result = verify_web_match(submitted_text, source_text)
    return result["score"]


def analyze_coherence(matches):
    """Groups matches by domain, flags ≥3 from same domain."""
    domain_counts = {}
    for m in matches:
        domain = urlparse(m['url']).netloc
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    
    for m in matches:
        domain = urlparse(m['url']).netloc
        if domain_counts[domain] >= 3:
            m['is_coherent'] = True
        else:
            m['is_coherent'] = False
    return matches
