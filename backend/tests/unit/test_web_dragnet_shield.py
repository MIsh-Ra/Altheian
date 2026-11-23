"""
Unit tests for Citation-Aware Web Dragnet Shield (Alethian v3.1).
Validates:
1. select_suspicious_chunks skips cited literature review chunks
2. select_suspicious_chunks selects unsourced suspicious chunks
3. run_dragnet grounds matches against BibliographyIndex and marks is_citation_grounded=True, is_excluded=True
4. Commercial homonym collisions (e.g., Yahoo Finance) are discarded
"""
import pytest
from unittest.mock import MagicMock, patch
from app.core.web_dragnet import select_suspicious_chunks, run_dragnet
from app.core.bibliography_extractor import build_bibliography_index


def test_select_suspicious_chunks_filters_citations():
    # Long cited passage with multiple distinct sentences
    cited_sentences = [
        "In Liang et al.’s landmark Patterns (2023) study, the authors systematically evaluated text detectors.",
        "They focused on standardized TOEFL essays written by non-native English speakers.",
        "They found that 61% of TOEFL essays were falsely flagged as machine generated [14].",
        "These empirical findings were corroborated by Hans et al. (2024) across medical corpora.",
        "Subsequent investigations revealed severe calibration errors under domain shift [18].",
        "Consequently, naive statistical thresholds cannot be safely relied upon in high-stakes pedagogy."
    ]
    cited_text = " ".join(cited_sentences)

    # Long unsourced suspicious passage with multiple distinct sentences
    unsourced_sentences = [
        "The proprietary algorithm utilizes a multi-layer perceptual hashing technique to compute similarity vectors.",
        "Vectors are compared across distributed index nodes without requiring prior tokenization overhead.",
        "This architectural innovation yields substantial latency reductions during large scale cluster retrieval.",
        "Experimental evaluations demonstrate sub-millisecond query execution on hundred-gigabyte shard datasets.",
        "Distributed synchronization primitives coordinate locking semantics across active replica instances.",
        "All benchmarked throughput metrics validate linear horizontal scalability under synthetic workloads."
    ]
    unsourced_text = " ".join(unsourced_sentences)

    doc_text = f"{cited_text}\n\n{unsourced_text}"

    # Default: skip_cited_chunks=True
    selected = select_suspicious_chunks(doc_text, skip_cited_chunks=True)

    # Should only select the unsourced chunks!
    assert len(selected) > 0
    for chunk in selected:
        assert "proprietary algorithm" in chunk["text"] or "Vectors are compared" in chunk["text"]
        assert "Patterns (2023)" not in chunk["text"]
        assert "[14]" not in chunk["text"]


@patch("app.core.web_dragnet.SerperClient")
def test_run_dragnet_grounds_and_excludes_cited_references(mock_serper_cls):
    body_sentences = [
        "The zero-shot detection baseline evaluates cross-perplexity metrics using pre-trained tokenizers.",
        "We analyze the behavior of token probability distributions across multiple model scales.",
        "Discrepancies in generated prose are measured against human written benchmarks under identical conditions.",
        "Curvature estimations quantify the localized geometry of log likelihood surfaces.",
        "Statistical divergence indicates whether candidate sequences inhabit negative curvature basins.",
        "Empirical validation confirms robust separation across diverse linguistic registers."
    ]
    body_text = " ".join(body_sentences)
    sample_doc = f"""{body_text}

References
[26] ACL 2026 Proceedings. https://aclanthology.org/2026.acl-long.1748.pdf
"""
    # Mock search client returning ACL paper URL
    mock_client = MagicMock()
    mock_client.search.return_value = [
        {
            "url": "https://aclanthology.org/2026.acl-long.1748/",
            "title": "Spotting LLMs With Binoculars - ACL Anthology",
            "snippet": "Spotting LLMs With Binoculars. In Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics."
        }
    ]
    mock_serper_cls.return_value = mock_client

    with patch("app.core.web_dragnet.compare_snippets", return_value=0.65):
        matches = run_dragnet(
            document_id="doc-test-1",
            text=sample_doc,
            grobid_references=[]
        )

    # The match should be grounded in the bibliography and excluded!
    assert len(matches) >= 1
    for match in matches:
        assert match["is_citation_grounded"] is True
        assert match["is_excluded"] is True
        assert "[26]" in match["exclude_reason"]
        assert "[Attributed]" in match["source_title"]


@patch("app.core.web_dragnet.SerperClient")
def test_run_dragnet_discards_commercial_homonym(mock_serper_cls):
    sample_doc = (
        "We analyze binoculars perplexity calculations across dense representations by evaluating "
        "log perplexity curvature and cross-entropy divergence between small and large neural architectures "
        "to distinguish machine generated sequences from genuine student composition."
    )

    mock_client = MagicMock()
    # Search returned Yahoo Finance binoculars market report
    mock_client.search.return_value = [
        {
            "url": "https://finance.yahoo.com/news/global-binoculars-market-report-2024.html",
            "title": "Global Optical Binoculars Market Size Forecast 2024-2030",
            "snippet": "The global binoculars market was valued at USD 1.2 billion and is projected to reach..."
        }
    ]
    mock_serper_cls.return_value = mock_client

    with patch("app.core.web_dragnet.compare_snippets", return_value=0.20):
        matches = run_dragnet(
            document_id="doc-test-2",
            text=sample_doc,
            grobid_references=[]
        )

    # Should discard commercial homonym collision
    assert len(matches) == 0
