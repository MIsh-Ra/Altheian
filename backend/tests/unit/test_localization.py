"""
Unit tests for WCP+NOT Change-Point Localization and Paragraph Risk Gradient Mapping:
- Weighted CUSUM + Narrowest-Over-Thresholding (NOT) change-point detection on token residuals.
- Paragraph risk gradient mapping from window score intervals to document character offsets.
"""

import numpy as np
import pytest
from app.core.ai_detection.localization import ChangePointDetector


def test_wcp_not_change_point_detection():
    """
    Tests the Weighted CUSUM + Narrowest-Over-Thresholding (NOT) algorithm
    on synthetic sequence of token residuals / binoculars scores.
    Demonstrates that given a document with human section (mean residual ~0.95)
    followed by AI section (mean residual ~0.70), WCP+NOT pinpoints the transition change-point.
    """
    detector = ChangePointDetector()

    # Reproducible synthetic sequence
    rng = np.random.RandomState(42)

    # 50 human tokens (mean ~0.95, low variance) + 50 AI tokens (mean ~0.70, low variance)
    n_human = 50
    n_ai = 50
    human_residuals = rng.normal(loc=0.95, scale=0.02, size=n_human)
    ai_residuals = rng.normal(loc=0.70, scale=0.02, size=n_ai)
    synthetic_series = np.concatenate([human_residuals, ai_residuals])

    # Run WCP+NOT change point detection
    change_points = detector.detect_change_points_not(
        series=synthetic_series,
        threshold=2.0,
        min_segment_len=10,
    )

    # Assert exactly one significant transition boundary is identified
    assert len(change_points) == 1
    detected_cp = change_points[0]

    # Change-point should be within +/- 2 indices of the true boundary (50)
    assert abs(detected_cp - 50) <= 2

    # Verify segment summary
    segments = detector.segment_series(synthetic_series, change_points=change_points)
    assert len(segments) == 2

    # Segment 1: Human section
    assert segments[0]["start_idx"] == 0
    assert segments[0]["end_idx"] == detected_cp
    assert pytest.approx(segments[0]["mean_score"], abs=0.05) == 0.95
    assert segments[0]["is_ai"] is False

    # Segment 2: AI section
    assert segments[1]["start_idx"] == detected_cp
    assert segments[1]["end_idx"] == 100
    assert pytest.approx(segments[1]["mean_score"], abs=0.05) == 0.70
    assert segments[1]["is_ai"] is True


def test_paragraph_risk_gradient_mapping():
    """
    Verifies that per-window score intervals are mapped to paragraph character
    offsets for heatmap display, generating [(start, end, score, is_ai)].
    """
    detector = ChangePointDetector()

    # Sample 3-paragraph document text
    p1 = (
        "In this historical retrospective, we examine the developmental trajectory "
        "of decentralized peer-to-peer computing from Napster through modern BitTorrent protocols."
    )
    p2 = (
        "Furthermore, it is important to realize that generative artificial intelligence "
        "exhibits distinct statistical properties in token frequency distributions across context windows."
    )
    p3 = (
        "Consequently, empirical observations demonstrate that human writing preserves "
        "subtle grammatical idiosyncrasies and lexical diversity absent in constrained decoding algorithms."
    )

    document_text = f"{p1}\n\n{p2}\n\n{p3}"

    # Calculate exact paragraph character spans
    p1_start = 0
    p1_end = len(p1)
    p2_start = document_text.index(p2)
    p2_end = p2_start + len(p2)
    p3_start = document_text.index(p3)
    p3_end = p3_start + len(p3)

    # Window intervals covering the text with different risk profiles
    # P1: Human (score 0.93)
    # P2: AI (score 0.72)
    # P3: Human (score 0.91)
    window_intervals = [
        (p1_start, p1_end, 0.9300, False),
        (p2_start, p2_end, 0.7200, True),
        (p3_start, p3_end, 0.9100, False),
    ]

    # Map intervals to paragraph-level heatmap segments
    mapped_paragraphs = detector.map_to_paragraphs(
        document_text=document_text,
        intervals=window_intervals,
        ai_threshold=0.8536,
    )

    assert len(mapped_paragraphs) == 3

    # Verify paragraph 1 (Human)
    assert mapped_paragraphs[0]["start_char"] == p1_start
    assert mapped_paragraphs[0]["end_char"] == p1_end
    assert mapped_paragraphs[0]["is_ai"] is False
    assert mapped_paragraphs[0]["score"] >= 0.8536
    assert mapped_paragraphs[0]["text"] == p1

    # Verify paragraph 2 (AI)
    assert mapped_paragraphs[1]["start_char"] == p2_start
    assert mapped_paragraphs[1]["end_char"] == p2_end
    assert mapped_paragraphs[1]["is_ai"] is True
    assert mapped_paragraphs[1]["score"] < 0.8536
    assert mapped_paragraphs[1]["text"] == p2

    # Verify paragraph 3 (Human)
    assert mapped_paragraphs[2]["start_char"] == p3_start
    assert mapped_paragraphs[2]["end_char"] == p3_end
    assert mapped_paragraphs[2]["is_ai"] is False
    assert mapped_paragraphs[2]["score"] >= 0.8536
    assert mapped_paragraphs[2]["text"] == p3

    # Verify tuple export format [(start, end, score, is_ai)]
    tuple_intervals = detector.extract_interval_tuples(mapped_paragraphs)
    assert len(tuple_intervals) == 3
    for entry in tuple_intervals:
        assert isinstance(entry, tuple)
        assert len(entry) == 4
        start, end, score, is_ai = entry
        assert isinstance(start, int)
        assert isinstance(end, int)
        assert isinstance(score, float)
        assert isinstance(is_ai, bool)
