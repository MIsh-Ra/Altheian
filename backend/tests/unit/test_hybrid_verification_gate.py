"""
Unit tests for the Two-Stage Hybrid Precision Gate (Alethian v3.2).
Validates:
1. calculate_longest_verbatim_run detects contiguous word subsequences.
2. calculate_token_jaccard computes normalized word set overlap.
3. verify_web_match accepts:
   - Verbatim runs >= 8 words
   - Lexical overlap >= 0.50
   - Dense semantic paraphrase (cosine >= 0.70 AND jaccard >= 0.35)
4. verify_web_match rejects topical coincidence / common domain knowledge (e.g. YOLO/BTP false positives).
"""
import pytest
from unittest.mock import patch
from app.core.content_fetcher import (
    calculate_longest_verbatim_run,
    calculate_token_jaccard,
    verify_web_match,
    compare_snippets,
)


def test_calculate_longest_verbatim_run():
    sub = "We propose an end-to-end neural network architecture for zero-shot text classification."
    src = "In this work, we propose an end-to-end neural network architecture for zero-shot text classification on noisy documents."
    
    run = calculate_longest_verbatim_run(sub, src)
    # "we propose an end-to-end neural network architecture for zero-shot text classification" -> 11 words
    assert run >= 10

    # Punctuation and casing differences
    sub2 = "Deep learning models, specifically transformers, have achieved remarkable results."
    src2 = "deep learning models specifically transformers have achieved remarkable results across diverse domains."
    run2 = calculate_longest_verbatim_run(sub2, src2)
    assert run2 >= 9


def test_calculate_token_jaccard():
    t1 = "the quick brown fox jumps over the lazy dog"
    t2 = "the fast brown fox jumps over that lazy dog"
    jaccard = calculate_token_jaccard(t1, t2)
    assert 0.60 <= jaccard <= 0.85

    # Completely disjoint
    t3 = "quantum computing superconduction qubit resonance"
    jaccard_disjoint = calculate_token_jaccard(t1, t3)
    assert jaccard_disjoint == 0.0


def test_verify_web_match_accepts_verbatim_run():
    submitted = (
        "We propose a novel framework that optimizes multi-head self-attention mechanisms "
        "by introducing sparse key-value caching across distributed worker nodes."
    )
    source = (
        "According to Smith et al., we propose a novel framework that optimizes multi-head "
        "self-attention mechanisms by introducing sparse key-value caching across distributed worker nodes."
    )
    # Long contiguous run of 18+ words
    with patch("app.core.content_fetcher.compare_snippets_cosine", return_value=0.85):
        result = verify_web_match(submitted, source)
    
    assert result["is_match"] is True
    assert result["match_type"] == "verbatim_run"
    assert result["verbatim_run"] >= 8
    assert result["score"] >= 0.50


def test_verify_web_match_accepts_lexical_alignment():
    # Paraphrased with substantial word re-ordering or partial substitutions (ratio >= 0.50)
    submitted = "The model optimizes cross-entropy loss by dynamically adjusting learning rate schedules during training iterations."
    source = "The model optimizes cross-entropy loss by dynamically adjusting learning rate schedules during the training iterations."
    
    with patch("app.core.content_fetcher.compare_snippets_cosine", return_value=0.60):
        result = verify_web_match(submitted, source)
    
    assert result["is_match"] is True
    assert result["lexical_ratio"] >= 0.50
    assert result["rejection_reason"] is None


def test_verify_web_match_accepts_dense_semantic_paraphrase():
    # Rewritten sentences with structural inversion: verbatim < 8, lexical < 0.50, cosine >= 0.70, jaccard >= 0.35
    submitted = "Convolutional layers automatically discover hierarchical spatial representations from raw pixel data during training."
    source = "From raw pixel data, spatial representations are automatically discovered by convolutional layers during model training."
    
    # Cosine = 0.78 (high), Jaccard = 0.73, Verbatim run = 4, Lexical ratio = 0.489
    with patch("app.core.content_fetcher.compare_snippets_cosine", return_value=0.78):
        result = verify_web_match(submitted, source)
    
    assert result["is_match"] is True
    assert result["match_type"] == "semantic_paraphrase"
    assert result["score"] == 0.78


def test_verify_web_match_rejects_topical_coincidence_btp_case():
    # Real false-positive case from BTP report:
    # Student describing YOLO training on cats and dogs
    student_text = (
        "For empirical validation of object detection, we trained a YOLOv8 network on a synthetic dataset "
        "of labeled cats and dogs images to observe bounding box regression error."
    )
    # Redmon et al. 2016 original YOLO paper snippet
    paper_snippet = (
        "You Only Look Once: Unified, Real-Time Object Detection. We present YOLO, a unified model for object detection. "
        "Prior detection systems repurpose classifiers to perform detection."
    )
    
    # Cosine similarity is topical (~0.45), but 0 verbatim runs and negligible lexical ratio
    with patch("app.core.content_fetcher.compare_snippets_cosine", return_value=0.45):
        result = verify_web_match(student_text, paper_snippet)
    
    assert result["is_match"] is False
    assert result["match_type"] == "topical_coincidence"
    assert result["score"] == 0.0
    assert "Common domain knowledge" in result["rejection_reason"]


def test_compare_snippets_returns_zero_on_rejected_match():
    text_a = "Deep neural networks are composed of multiple layers of nonlinear processing units."
    text_b = "Convolutional neural networks utilize convolutional filters to extract hierarchical features from images."
    
    with patch("app.core.content_fetcher.compare_snippets_cosine", return_value=0.40):
        score = compare_snippets(text_a, text_b)
    
    assert score == 0.0
