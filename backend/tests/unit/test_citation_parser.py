"""
Unit tests for Academic Citation Parser Engine (Alethian v3.1).
Validates four citation families:
1. Bracketed numerical citations: [1], [12, 14], [1-5]
2. Author-year parentheticals: (Liang et al., 2023), (Smith, 2024; Jones, 2022)
3. Superscripts & caret notations: ^9, ^60, ¹, ², ³
4. Attributive lead-ins & author-tool attribution
"""
import pytest
from app.core.citation_parser import parse_citations_in_chunk, has_citations


def test_bracketed_single():
    text = "Recent benchmarks indicate that transformer models exhibit catastrophic forgetting [14]."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is True
    assert len(profile.markers) == 1
    marker = profile.markers[0]
    assert marker.marker_type == "bracketed"
    assert "14" in marker.citation_keys
    assert has_citations(text) is True


def test_bracketed_comma_list():
    text = "State-of-the-art architectures rely heavily on self-attention [12, 14, 18]."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is True
    assert len(profile.markers) == 1
    assert profile.markers[0].citation_keys == ["12", "14", "18"]


def test_bracketed_range():
    text = "Several surveys cover zero-shot LLM detection in depth [1-4]."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is True
    assert profile.markers[0].citation_keys == ["1", "2", "3", "4"]


def test_author_year_citations():
    text = "As shown by previous evaluations (Liang et al., 2023), non-native English essays suffer high false-positive rates."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is True
    assert any(m.marker_type == "author_year" for m in profile.markers)
    assert has_citations(text) is True


def test_author_year_multiple():
    text = "Perplexity-based methods are sensitive to prompt length (Hans et al., 2024; Mitchell et al., 2023)."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is True
    keys = profile.markers[0].citation_keys
    assert any("Hans" in k for k in keys)
    assert any("Mitchell" in k for k in keys)


def test_caret_superscript():
    text = "The evaluated model achieved a state-of-the-art AUROC^9 on the XSum benchmark."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is True
    caret_markers = [m for m in profile.markers if m.marker_type == "superscript"]
    assert len(caret_markers) >= 1
    assert "9" in caret_markers[0].citation_keys


def test_attached_superscript():
    text = "Full mathematical proofs and derivations^60 are included in the supplementary materials."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is True
    assert any("60" in m.citation_keys for m in profile.markers)


def test_unicode_superscript():
    text = "Prior experiments confirm this hypothesis¹²³ across all target domains."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is True
    assert any(m.citation_keys == ["123"] for m in profile.markers)


def test_attributive_leadin():
    text = "In Liang et al.’s landmark Patterns (2023) study, the authors documented bias against non-native writers."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is True
    assert any(m.marker_type == "attributive" for m in profile.markers)


def test_author_tool_attribution():
    text = "Fast-DetectGPT's authors updated their repository to address tokenization discrepancies."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is True
    assert any("Fast-DetectGPT" in m.citation_keys for m in profile.markers)


def test_uncited_prose():
    text = "We propose a novel framework that integrates multi-stage neural classifiers with deterministic routing pipelines."
    profile = parse_citations_in_chunk(text)
    assert profile.is_cited is False
    assert len(profile.markers) == 0
    assert has_citations(text) is False
