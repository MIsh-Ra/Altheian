"""
Unit tests for Stage 2 Escalation Audit:
- Llama-3-8B Implicit Reward Model (IRM) DPO closed-form ratio.
- DeBERTa-v3 Academic Classifier FP32 numerical stability.
- Multi-metric consensus decision logic (Tier 0 Human, Tier 2 Mixed AI, Tier 3 Elevated AI).
"""

from unittest.mock import MagicMock

import pytest
import torch
from app.core.ai_detection.escalation import (
    ConsensusResult,
    Stage2EscalationAudit,
    VerdictTier,
)


def test_irm_implicit_reward_ratio():
    """
    Verifies the closed-form DPO log-policy ratio calculation between
    aligned instruct model and base reference model:
        r_IRM(s) = (1 / N) * sum(log(P_pi / P_ref)) = (1 / N) * sum(log(P_pi) - log(P_ref))
    """
    audit = Stage2EscalationAudit()

    # Synthetic token log-probabilities
    # Aligned instruct model places higher probability on instruction-tuned AI text
    log_probs_instruct = torch.tensor(
        [-1.20, -0.95, -1.10, -0.80, -1.05], dtype=torch.float32
    )
    log_probs_base = torch.tensor(
        [-2.10, -2.30, -2.00, -1.90, -2.15], dtype=torch.float32
    )

    # Expected: (1/5) * sum([0.90, 1.35, 0.90, 1.10, 1.10]) = 5.35 / 5 = 1.07
    expected_ratio = float(torch.mean(log_probs_instruct - log_probs_base).item())
    computed_ratio = audit.compute_irm_ratio(log_probs_instruct, log_probs_base)

    assert pytest.approx(computed_ratio, rel=1e-5) == expected_ratio
    assert computed_ratio > 0.0  # Aligned model preferred this sequence

    # Human text where base model has equal or higher probability
    human_log_probs_instruct = torch.tensor([-2.5, -3.0, -2.8], dtype=torch.float32)
    human_log_probs_base = torch.tensor([-2.1, -2.6, -2.4], dtype=torch.float32)
    human_ratio = audit.compute_irm_ratio(
        human_log_probs_instruct, human_log_probs_base
    )

    assert human_ratio < 0.0

    # Test tensor logits extraction helper
    vocab_size = 50
    seq_len = 8
    mock_instruct_logits = torch.randn(1, seq_len, vocab_size, dtype=torch.float32)
    mock_base_logits = torch.randn(1, seq_len, vocab_size, dtype=torch.float32)
    mock_input_ids = torch.randint(0, vocab_size, (1, seq_len), dtype=torch.long)

    logits_ratio = audit.compute_irm_from_logits(
        instruct_logits=mock_instruct_logits,
        base_logits=mock_base_logits,
        input_ids=mock_input_ids,
    )
    assert isinstance(logits_ratio, float)


def test_deberta_fp32_runner():
    """
    Verifies that the academic classifier inference executes strictly in torch.float32
    (preventing DeBERTa FP16 numerical instability) and outputs valid softmax probabilities.
    """
    audit = Stage2EscalationAudit()

    # Mock DeBERTa model and tokenizer
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()

    # Configure mock tokenizer to return tensors
    mock_tokenizer.return_value = {
        "input_ids": torch.tensor([[101, 2054, 2003, 102]], dtype=torch.long),
        "attention_mask": torch.tensor([[1, 1, 1, 1]], dtype=torch.long),
    }

    # Simulate logits output - class 0 = Human, class 1 = AI
    raw_logits = torch.tensor([[-1.5, 2.5]], dtype=torch.float32)
    mock_output = MagicMock()
    mock_output.logits = raw_logits
    mock_model.return_value = mock_output

    result = audit.run_deberta_inference(
        model=mock_model,
        tokenizer=mock_tokenizer,
        text="This is an academic passage being evaluated.",
        device="cpu",
    )

    # Assert model execution was verified in float32
    assert result["dtype"] == "torch.float32"
    assert "ai_probability" in result
    assert "human_probability" in result

    # Probabilities must sum to 1.0
    p_ai = result["ai_probability"]
    p_human = result["human_probability"]
    assert pytest.approx(p_ai + p_human, abs=1e-5) == 1.0

    # With logits [-1.5, 2.5], AI should have higher probability
    expected_softmax = torch.softmax(raw_logits, dim=-1)
    assert pytest.approx(p_ai, abs=1e-4) == expected_softmax[0, 1].item()
    assert p_ai > 0.90

    # Test with simulated FP16 logits input to verify automatic upcasting to FP32
    fp16_logits = torch.tensor([[1.0, 3.0]], dtype=torch.float16)
    upcast_res = audit.predict_deberta_from_logits(fp16_logits)
    assert upcast_res["dtype"] == "torch.float32"
    assert (
        pytest.approx(
            upcast_res["ai_probability"] + upcast_res["human_probability"], abs=1e-5
        )
        == 1.0
    )


def test_stage2_consensus_voting():
    """
    Tests that when Binoculars, DNA-DetectLLM, IRM, and DeBERTa signals
    are evaluated together, the multi-metric consensus correctly resolves into:
    - Tier 0 (Human)
    - Tier 2 (Mixed AI)
    - Tier 3 (Elevated AI)
    """
    audit = Stage2EscalationAudit()

    # 1. Clean Human Document (All signals clear)
    # Stage 1 Binoculars >= 0.9015, DNA >= 0.85, IRM < 0.0, DeBERTa < 0.2
    human_verdict = audit.evaluate_consensus(
        stage1_binoculars=0.9250,
        stage2_binoculars=0.9180,
        dna_score=0.8900,
        irm_score=-0.1200,
        deberta_prob=0.0800,
    )
    assert isinstance(human_verdict, ConsensusResult)
    assert human_verdict.verdict_tier == VerdictTier.T0_HUMAN
    assert "Human" in human_verdict.tier_label
    assert human_verdict.flags["binoculars_ai"] is False
    assert human_verdict.flags["deberta_ai"] is False

    # 2. Mixed AI / Borderline Document (Corroborated by Stage 2)
    # Binoculars in [0.8350, 0.8536], DNA flagged, IRM positive, DeBERTa 0.5-0.8
    mixed_verdict = audit.evaluate_consensus(
        stage1_binoculars=0.8420,
        stage2_binoculars=0.8450,
        dna_score=0.7100,  # flagged (< 0.75)
        irm_score=0.2200,  # flagged (> 0.15)
        deberta_prob=0.6800,  # 0.5 - 0.8
    )
    assert mixed_verdict.verdict_tier == VerdictTier.T2_ELEVATED
    assert "Mixed AI" in mixed_verdict.tier_label or "Mixed" in mixed_verdict.tier_label
    assert mixed_verdict.flags["dna_ai"] is True
    assert mixed_verdict.flags["irm_ai"] is True

    # 3. High-Confidence Elevated AI Document (Strong consensus across 3+ signals)
    # Binoculars < 0.8350, DNA < 0.70, IRM > 0.30, DeBERTa > 0.85
    elevated_verdict = audit.evaluate_consensus(
        stage1_binoculars=0.8120,
        stage2_binoculars=0.8050,
        dna_score=0.6200,
        irm_score=0.4800,
        deberta_prob=0.9400,
    )
    assert elevated_verdict.verdict_tier == VerdictTier.T3_HIGH
    assert (
        "Elevated AI" in elevated_verdict.tier_label
        or "AI" in elevated_verdict.tier_label
    )
    assert elevated_verdict.confidence >= 0.85
