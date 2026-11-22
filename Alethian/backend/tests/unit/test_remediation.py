"""
Unit tests for v2.0 engine remediation:
- Substantive word counting (ignoring TOC dotted leaders)
- Twin document 85% coverage clamp
- Interval-merged heatmap density calculation
- Search key persistence to Redis
- SerpApi vs Serper dual-gateway detection
"""
import pytest
from unittest.mock import MagicMock, patch

from app.core.report_engine import (
    calculate_originality,
    generate_heatmap,
    _count_substantive_words,
)
from app.api.admin import update_config, get_config
from app.schemas.admin import AdminConfigUpdate
from app.core.web_dragnet import SerperClient


class TestSubstantiveWordCount:
    def test_substantive_word_count(self):
        """
        Verify that a string of punctuation/dots like '. . . . . . . 12' has 0 substantive words,
        while 'Chapter 1 Introduction to AI' has 5 words.
        """
        toc_dots = ". . . . . . . 12"
        assert _count_substantive_words(toc_dots) == 0
        assert _count_substantive_words(". . . . . . .") == 0

        prose = "Chapter 1 Introduction to AI"
        assert _count_substantive_words(prose) == 5


class TestOriginalityRemediation:
    def test_originality_substantive_tokens(self):
        """
        When TOC dots are present in the document, passing the actual text allows
        substantive word counting in the denominator, properly reflecting true coverage.
        """
        real_prose = "Introduction to machine learning algorithms and neural network architectures."
        prose_word_count = len(real_prose.split())  # 9 words
        toc_filler = ". . . . " * 30  # 120 dot tokens
        doc_text = real_prose + " " + toc_filler
        total_raw_tokens = len(doc_text.split())  # 129 tokens

        # A match covering 100% of the substantive prose
        matches = [{
            "submitted_text": real_prose,
            "submitted_start_char": 0,
            "submitted_end_char": len(real_prose),
            "is_excluded": False,
        }]

        # Without doc_text, denominator is total_raw_tokens (129), diluting plagiarism coverage
        score_without_doc_text = calculate_originality(matches, doc_word_count=total_raw_tokens)
        assert score_without_doc_text > 70.0  # Falsely high originality due to TOC dots inflation

        # With doc_text, substantive word counting is used -> coverage is 100% -> clamped to 0.0%
        score_with_doc_text = calculate_originality(matches, doc_word_count=total_raw_tokens, doc_text=doc_text)
        assert score_with_doc_text == 0.0

    def test_twin_document_85_percent_clamp(self):
        """
        When substantive match coverage exceeds 85%, calculate_originality must return 0.0% (100% plagiarism).
        """
        words = ["word" + str(i) for i in range(100)]
        doc_text = " ".join(words)  # exactly 100 substantive words

        # Case 1: 50% coverage -> originality around 50%
        text_50 = " ".join(words[:50])
        matches_50 = [{
            "submitted_text": text_50,
            "submitted_start_char": 0,
            "submitted_end_char": len(text_50),
            "is_excluded": False,
        }]
        score_50 = calculate_originality(matches_50, doc_word_count=100, doc_text=doc_text)
        assert score_50 == pytest.approx(50.0, abs=1.0)

        # Case 2: 86% coverage (> 85%) -> must clamp strictly to 0.0%
        text_86 = " ".join(words[:86])
        matches_86 = [{
            "submitted_text": text_86,
            "submitted_start_char": 0,
            "submitted_end_char": len(text_86),
            "is_excluded": False,
        }]
        score_86 = calculate_originality(matches_86, doc_word_count=100, doc_text=doc_text)
        assert score_86 == 0.0

        # Case 3: 95% coverage -> clamped to 0.0%
        text_95 = " ".join(words[:95])
        matches_95 = [{
            "submitted_text": text_95,
            "submitted_start_char": 0,
            "submitted_end_char": len(text_95),
            "is_excluded": False,
        }]
        score_95 = calculate_originality(matches_95, doc_word_count=100, doc_text=doc_text)
        assert score_95 == 0.0


class TestHeatmapRemediation:
    def test_heatmap_density_merged_intervals(self):
        """
        Test that overlapping matches on the same page have their intervals merged before computing density.
        If a 500-word page has 5 overlapping 30-word matches that all cover the same character range
        [100:250] (approx 25 words), the density must be ~25/500 = 0.05, NOT 150/500 = 0.30.
        Density must never exceed 1.0.
        """
        # 5 identical overlapping matches covering chars 100 to 250 (150 chars = ~25 words)
        matches = [
            {
                "submitted_text": "sample text " * 5,
                "submitted_page": 1,
                "submitted_start_char": 100,
                "submitted_end_char": 250,
                "type": "internal",
                "is_excluded": False,
            }
            for _ in range(5)
        ]

        heatmap = generate_heatmap(matches, page_count=1, doc_word_count=500)
        assert len(heatmap) == 1
        page1 = heatmap[0]

        # Merged interval density: 25 / 500 = 0.05
        # Without merging, naive sum is 5 * 30 = 150 words -> 150 / 500 = 0.30
        assert page1["density_score"] == pytest.approx(0.05, abs=0.01)
        assert page1["density_score"] <= 1.0

        # Also test massive overlap capped at 1.0
        massive_matches = [
            {
                "submitted_text": "huge text " * 100,
                "submitted_page": 1,
                "submitted_start_char": 0,
                "submitted_end_char": 6000,
                "type": "internal",
                "is_excluded": False,
            }
            for _ in range(10)
        ]
        heatmap_capped = generate_heatmap(massive_matches, page_count=1, doc_word_count=500)
        assert heatmap_capped[0]["density_score"] <= 1.0


class TestAdminKeyPersistence:
    def test_admin_key_persistence(self):
        """
        Verify that updating config saves serper_api_key to redis under 'config:serper_api_key' and returns it.
        """
        mock_redis = MagicMock()
        mock_db = MagicMock()
        mock_user = MagicMock()

        with patch("redis.Redis", return_value=mock_redis):
            update_req = AdminConfigUpdate(serper_api_key="test_serper_secret_key_123")
            result = update_config(update_req, db=mock_db, current_user=mock_user)

            # Check that redis set was called with 'config:serper_api_key'
            mock_redis.set.assert_called_with("config:serper_api_key", "test_serper_secret_key_123")
            # Result should return the updated key or message
            assert "serper_api_key" in result or result.get("message") == "Configuration updated"
            if "serper_api_key" in result:
                assert result["serper_api_key"] == "test_serper_secret_key_123"


class TestWebDragnetSerpApiSupport:
    def test_web_dragnet_serpapi_support(self):
        """
        Verify that SerperClient detects SerpApi keys or URLs and configures appropriately.
        """
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch("redis.Redis", return_value=mock_redis):
            # Test default / Serper.dev detection
            with patch.dict("os.environ", {"SERPER_API_KEY": "serper_dev_key_abc"}):
                client_serper = SerperClient()
                assert getattr(client_serper, "engine_type", "serper") == "serper" or "google.serper.dev" in getattr(client_serper, "endpoint", "")

            # Test SerpApi key detection (e.g. key prefixed with serpapi_ or URL set to serpapi)
            with patch.dict("os.environ", {"SERPER_API_KEY": "serpapi_secret_key_xyz"}):
                client_serpapi = SerperClient()
                assert getattr(client_serpapi, "engine_type", None) == "serpapi" or "serpapi.com" in getattr(client_serpapi, "endpoint", "")

            # Test Redis key reading
            mock_redis.get.side_effect = lambda k: "redis_serpapi_key" if k == "config:serper_api_key" else None
            with patch.dict("os.environ", {}, clear=True):
                client_from_redis = SerperClient()
                assert client_from_redis.api_key == "redis_serpapi_key"
                assert getattr(client_from_redis, "engine_type", None) == "serpapi"
