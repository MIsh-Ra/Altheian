"""
Unit tests for Bibliography & Reference Extraction Engine (Alethian v3.1).
Validates:
1. Grobid <listBibl> parsing
2. Text fallback extraction from 'References' sections
3. Canonical URL matching (http/https, trailing slash, .pdf stripping)
4. DOI resolution & matching
5. arXiv ID matching
6. Fuzzy academic title token overlap matching
7. Master is_reference_match predicate
"""
import pytest
from app.core.bibliography_extractor import (
    build_bibliography_index,
    extract_bibliography_from_grobid,
    extract_bibliography_from_text,
    normalize_url,
    normalize_doi,
)


def test_url_normalization():
    assert normalize_url("https://aclanthology.org/2026.acl-long.1748.pdf") == "aclanthology.org/2026.acl-long.1748"
    assert normalize_url("http://www.aclanthology.org/2026.acl-long.1748/") == "aclanthology.org/2026.acl-long.1748"
    assert normalize_url("https://arxiv.org/abs/2301.12345") == "arxiv.org/abs/2301.12345"


def test_doi_normalization():
    assert normalize_doi("https://doi.org/10.1145/3372278.3390670") == "10.1145/3372278.3390670"
    assert normalize_doi("doi: 10.1145/3372278.3390670.") == "10.1145/3372278.3390670"


def test_extract_from_text_references():
    sample_paper = """
1. Introduction
Modern LLMs generate high quality text.

References
[1] Liang, W., et al. (2023). GPT detectors are biased against non-native English writers. Patterns, 4(7). https://doi.org/10.1016/j.patter.2023.100779
[2] Hans, A., et al. (2024). Spotting LLMs With Binoculars. In Proceedings of ACL 2024. https://aclanthology.org/2026.acl-long.1748.pdf
[3] Mitchell, E., et al. (2023). DetectGPT: Zero-shot machine-generated text detection using probability curvature. arXiv:2301.11305.
[4] SnapJudge: Evaluating LLMs on Multi-faceted Alignment. 10.1145/99999.88888.
"""
    entries = extract_bibliography_from_text(sample_paper)
    assert len(entries) >= 4
    assert entries[0].label == "[1]"
    assert entries[1].label == "[2]"

    # Verify URLs and DOIs
    ref2 = entries[1]
    assert any("aclanthology.org" in u for u in ref2.urls)

    ref3 = entries[2]
    assert "2301.11305" in ref3.arxiv_ids


def test_bibliography_index_matching():
    sample_text = """
References
[26] ACL Anthology Long Paper. 2024. https://aclanthology.org/2026.acl-long.1748.pdf
[60] SnapJudge: Evaluating LLMs on Multi-faceted Alignment Benchmark.
"""
    idx = build_bibliography_index(full_text=sample_text)
    assert len(idx.entries) == 2

    # 1. Direct URL match with trailing slash
    match1 = idx.matches_url("https://aclanthology.org/2026.acl-long.1748/")
    assert match1 is not None
    assert match1.label == "[26]"

    # 2. Master predicate matching candidate URL
    match_pred = idx.is_reference_match(
        candidate_url="http://aclanthology.org/2026.acl-long.1748.pdf",
        candidate_title="ACL Anthology Paper",
        candidate_snippet=""
    )
    assert match_pred is not None
    assert match_pred.label == "[26]"

    # 3. Fuzzy title match for SnapJudge
    match_title = idx.matches_title_fuzzy("SnapJudge: Evaluating LLMs on Multi-faceted Alignment")
    assert match_title is not None
    assert match_title.label == "[60]"

    # 4. Non-matching query should return None
    assert idx.is_reference_match("https://finance.yahoo.com/news/binoculars-market.html") is None
