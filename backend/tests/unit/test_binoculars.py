"""
Unit tests for Stage 1 Dual-Metric Zero-Shot AI Detection Engine (Binoculars + DNA-DetectLLM).
Verifies:
1. ModelManager singleton initialization, GPU assignments, fp16 + sdpa attention loading.
2. FP32 logit upcast numerical stability preventing overflow on extreme dynamic ranges.
3. Binoculars ratio formula log(PPL_M2) / log(xPPL_M1, M2).
4. DNA-DetectLLM greedy template token divergence co-metric.
5. 512-token sliding window context chunker with stride 256 and 128-token warmup discard.
6. Evidentiary tier classification (T0_HUMAN, T1_INDETERMINATE, ESCALATE).
"""

from unittest.mock import MagicMock, patch

import pytest
import torch
import torch.nn.functional as F

try:
    from app.core.ai_detection.binoculars import (
        BinocularsScorer,
        chunk_tokens_sliding_window,
        classify_evidentiary_tier,
        stitch_sliding_window_scores,
        upcast_logits_to_fp32,
    )
    from app.core.ai_detection.dna_detect import DNADetectScorer
    from app.core.ai_detection.model_manager import ModelManager
except ImportError:
    from backend.app.core.ai_detection.binoculars import (
        BinocularsScorer,
        chunk_tokens_sliding_window,
        classify_evidentiary_tier,
        stitch_sliding_window_scores,
        upcast_logits_to_fp32,
    )
    from backend.app.core.ai_detection.dna_detect import DNADetectScorer
    from backend.app.core.ai_detection.model_manager import ModelManager


def test_model_manager_singleton_initialization():
    """
    Verifies ModelManager manages GPU assignments and loads causal LLM configs properly
    with torch_dtype=torch.float16, attn_implementation='sdpa', use_cache=False, and model.eval().
    """
    # Reset singleton instance for isolated test
    ModelManager._instance = None

    manager1 = ModelManager.get_instance()
    manager2 = ModelManager.get_instance()
    assert manager1 is manager2, "ModelManager must be a strict singleton"

    # Mock AutoModelForCausalLM and AutoTokenizer from transformers
    with (
        patch("transformers.AutoModelForCausalLM.from_pretrained") as mock_model_loader,
        patch("transformers.AutoTokenizer.from_pretrained") as mock_tokenizer_loader,
    ):
        mock_obs_model = MagicMock()
        mock_perf_model = MagicMock()
        mock_obs_model.config.use_cache = True
        mock_perf_model.config.use_cache = True

        mock_model_loader.side_effect = [mock_obs_model, mock_perf_model]
        mock_tok = MagicMock()
        mock_tokenizer_loader.return_value = mock_tok

        manager1.load_models(
            observer_name="tiiuae/falcon-7b",
            performer_name="tiiuae/falcon-7b-instruct",
            observer_device="cuda:0",
            performer_device="cuda:1",
        )

        assert mock_model_loader.call_count == 2, (
            "Both observer and performer models must be loaded"
        )

        # Check call arguments for observer and performer
        calls = mock_model_loader.call_args_list

        obs_call_args, obs_call_kwargs = calls[0]
        assert obs_call_args[0] == "tiiuae/falcon-7b"
        assert obs_call_kwargs.get("torch_dtype") == torch.float16
        assert obs_call_kwargs.get("attn_implementation") == "sdpa"

        perf_call_args, perf_call_kwargs = calls[1]
        assert perf_call_args[0] == "tiiuae/falcon-7b-instruct"
        assert perf_call_kwargs.get("torch_dtype") == torch.float16
        assert perf_call_kwargs.get("attn_implementation") == "sdpa"

        # Verify evaluation mode and cache disabled
        mock_obs_model.eval.assert_called_once()
        mock_perf_model.eval.assert_called_once()
        assert mock_obs_model.config.use_cache is False
        assert mock_perf_model.config.use_cache is False

        # Verify GPU assignments
        assert manager1.observer_device == "cuda:0"
        assert manager1.performer_device == "cuda:1"


def test_fp32_logit_upcast_stability():
    """
    Generates synthetic logit tensors with large dynamic ranges (including extreme
    values like 60,000.0) and verifies that casting to float32 before F.log_softmax
    and F.softmax prevents FP16 overflow and outputs zero NaNs or Infs.
    """
    # In FP16, maximum finite value is 65504. Exponentiating numbers near 60,000 in FP16 overflows to inf.
    extreme_logits = torch.tensor(
        [
            [-60000.0, 0.0, 60000.0, 59990.0],
            [60000.0, 60000.0, -50000.0, 10.0],
            [-65000.0, -60000.0, -1000.0, 0.0],
        ],
        dtype=torch.float16,
    )

    log_probs, probs = upcast_logits_to_fp32(extreme_logits)

    # Output tensors must be FP32
    assert log_probs.dtype == torch.float32
    assert probs.dtype == torch.float32

    # Verification: Zero NaNs and Zero Infs
    assert not torch.isnan(log_probs).any(), "log_probs contains NaNs"
    assert not torch.isinf(log_probs).any(), "log_probs contains Infs"
    assert not torch.isnan(probs).any(), "probs contains NaNs"
    assert not torch.isinf(probs).any(), "probs contains Infs"

    # Softmax probabilities should sum to 1.0 along the vocabulary axis
    sums = probs.sum(dim=-1)
    assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5), (
        "Softmax probabilities must sum to 1"
    )

    # All probabilities must be in [0.0, 1.0]
    assert (probs >= 0.0).all() and (probs <= 1.0).all()


def test_binoculars_ratio_formula():
    """
    Uses synthetic observer logits and performer logits to compute Performer Log-PPL
    and Cross-PPL, verifying the ratio log(PPL_M2) / log(xPPL_M1, M2) matches mathematical
    expectations.
    """
    torch.manual_seed(42)
    batch_size = 2
    seq_len = 10
    vocab_size = 50

    input_ids = torch.randint(0, vocab_size, (batch_size, seq_len))
    # Synthetic logits for observer (M1) and performer (M2)
    obs_logits = torch.randn(batch_size, seq_len, vocab_size, dtype=torch.float16)
    perf_logits = torch.randn(batch_size, seq_len, vocab_size, dtype=torch.float16)

    scorer = BinocularsScorer()
    result = scorer.compute_score_from_logits(obs_logits, perf_logits, input_ids)

    # Compute expected mathematical values manually with FP32 precision
    shift_labels = input_ids[:, 1:].contiguous()
    shift_perf_logits = perf_logits[:, :-1, :].contiguous().float()
    shift_obs_logits = obs_logits[:, :-1, :].contiguous().float()

    log_q = F.log_softmax(shift_perf_logits, dim=-1)
    p_obs = F.softmax(shift_obs_logits, dim=-1)

    # Performer Log-PPL = - 1/|I| sum log P_M2(x_i | x_<i)
    # Gather the log prob of observed target tokens
    gathered_log_q = torch.gather(
        log_q, dim=-1, index=shift_labels.unsqueeze(-1)
    ).squeeze(-1)
    expected_performer_log_ppl = -gathered_log_q.mean().item()

    # Cross-PPL = - 1/|I| sum_i sum_v p_M1(v | x_<i) * log p_M2(v | x_<i)
    expected_cross_ppl = -(p_obs * log_q).sum(dim=-1).mean().item()

    expected_binoculars_ratio = expected_performer_log_ppl / expected_cross_ppl

    assert (
        pytest.approx(expected_performer_log_ppl, rel=1e-5) == result.performer_log_ppl
    )
    assert pytest.approx(expected_cross_ppl, rel=1e-5) == result.cross_ppl
    assert pytest.approx(expected_binoculars_ratio, rel=1e-5) == result.binoculars_score


def test_dna_detectllm_greedy_template():
    """
    Uses performer logits to select greedy top-1 tokens (-log_q.max(dim=-1).values)
    and computes the template divergence ratio.
    """
    torch.manual_seed(123)
    batch_size = 1
    seq_len = 8
    vocab_size = 30

    input_ids = torch.randint(0, vocab_size, (batch_size, seq_len))
    obs_logits = torch.randn(batch_size, seq_len, vocab_size, dtype=torch.float16)
    perf_logits = torch.randn(batch_size, seq_len, vocab_size, dtype=torch.float16)

    dna_scorer = DNADetectScorer()
    dna_result = dna_scorer.compute_score_from_logits(
        obs_logits, perf_logits, input_ids
    )

    # Manual verification
    shift_perf_logits = perf_logits[:, :-1, :].contiguous().float()
    shift_obs_logits = obs_logits[:, :-1, :].contiguous().float()
    shift_labels = input_ids[:, 1:].contiguous()

    log_q = F.log_softmax(shift_perf_logits, dim=-1)
    p_obs = F.softmax(shift_obs_logits, dim=-1)

    # Greedy top-1 tokens: max value of log_q at each sequence position
    greedy_log_probs = log_q.max(dim=-1).values
    expected_template_nll = -greedy_log_probs.mean().item()

    expected_cross_ppl = -(p_obs * log_q).sum(dim=-1).mean().item()
    expected_sigma = expected_template_nll / expected_cross_ppl

    gathered_log_q = torch.gather(
        log_q, dim=-1, index=shift_labels.unsqueeze(-1)
    ).squeeze(-1)
    expected_binoculars = (-gathered_log_q.mean().item()) / expected_cross_ppl

    expected_composite_r = 0.5 * (expected_binoculars + expected_sigma)

    assert (
        pytest.approx(expected_sigma, rel=1e-5) == dna_result.template_divergence_ratio
    )
    assert pytest.approx(expected_composite_r, rel=1e-5) == dna_result.composite_score


def test_sliding_window_context_chunker():
    """
    Tests token sequence partitioning into 512-token windows with stride 256,
    verifying non-initial windows discard the first 128 warmup tokens when stitching results.
    """
    total_tokens = 1000
    token_sequence = list(range(total_tokens))

    windows = chunk_tokens_sliding_window(token_sequence, window_size=512, stride=256)

    # With 1000 tokens, window size 512, stride 256:
    # Window 0: [0:512] (512 tokens)
    # Window 1: [256:768] (512 tokens)
    # Window 2: [512:1000] (488 tokens, partial or padded)
    assert len(windows) == 3
    assert windows[0].start_idx == 0
    assert windows[0].end_idx == 512
    assert len(windows[0].tokens) == 512
    assert windows[0].warmup_discard == 0, "Window 0 should not discard initial tokens"

    assert windows[1].start_idx == 256
    assert windows[1].end_idx == 768
    assert len(windows[1].tokens) == 512
    assert windows[1].warmup_discard == 128, (
        "Window 1 must discard first 128 warmup tokens"
    )

    assert windows[2].start_idx == 512
    assert windows[2].end_idx == 1000
    assert windows[2].warmup_discard == 128, (
        "Window 2 must discard first 128 warmup tokens"
    )

    # Now verify stitching per-token scores:
    # Mock scores for each window
    window_per_token_scores = [
        [1.0] * len(windows[0].tokens),
        [2.0] * len(windows[1].tokens),
        [3.0] * len(windows[2].tokens),
    ]

    stitched_scores = stitch_sliding_window_scores(
        windows, window_per_token_scores, warmup_tokens=128
    )

    # Verify length of stitched scores matches total tokens
    assert len(stitched_scores) == total_tokens

    # Tokens 0..255 only received Window 0's score (1.0)
    assert stitched_scores[0] == 1.0
    assert stitched_scores[255] == 1.0

    # In Window 1 (starts at 256), the first 128 tokens (indices 256..383) are discarded as warmup.
    # Therefore, at token 300, Window 1 contributed nothing (discarded); Window 0 still covered up to 512.
    assert stitched_scores[300] == 1.0

    # From token 384 onwards, Window 1's non-warmup tokens (indices 384..767) are retained.
    # Window 2 starts at 512 and discards first 128 (512..639).
    # Token 700 is after Window 2 warmup (640..999) and within Window 1, so Window 2 (3.0) contributes.
    assert stitched_scores[900] == 3.0


def test_evidentiary_tier_classification():
    """
    Asserts calibrated for Qwen2.5:
    score < 1.01 -> 'T0_HUMAN'
    1.01 <= score < 1.07 -> 'T1_INDETERMINATE'
    score >= 1.07 -> 'ESCALATE'
    """
    assert classify_evidentiary_tier(0.9500) == "T0_HUMAN"
    assert classify_evidentiary_tier(1.009) == "T0_HUMAN"
    assert classify_evidentiary_tier(1.010) == "T1_INDETERMINATE"
    assert classify_evidentiary_tier(1.045) == "T1_INDETERMINATE"
    assert classify_evidentiary_tier(1.069) == "T1_INDETERMINATE"
    assert classify_evidentiary_tier(1.070) == "ESCALATE"
    assert classify_evidentiary_tier(1.150) == "ESCALATE"
    assert classify_evidentiary_tier(1.266) == "ESCALATE"
