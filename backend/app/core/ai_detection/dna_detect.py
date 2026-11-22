"""
DNA-DetectLLM scoring engine (Template Divergence Ratio).
Computes greedy ideal-AI template token divergence from performer logits (-log_q.max(dim=-1).values)
and blends it into the Stage 1 composite score: R(s) = 0.5 * (B(s) + sigma(s)).
"""

from __future__ import annotations

import logging

import torch
from pydantic import BaseModel, Field

from .binoculars import (
    chunk_tokens_sliding_window,
    classify_evidentiary_tier,
    upcast_logits_to_fp32,
)
from .model_manager import ModelManager

logger = logging.getLogger(__name__)


class DNADetectResult(BaseModel):
    """Structured output for DNA-DetectLLM co-metric evaluation."""

    binoculars_score: float = Field(..., description="Base Binoculars ratio B(s)")
    template_divergence_ratio: float = Field(
        ..., description="Greedy template divergence ratio sigma(s)"
    )
    composite_score: float = Field(
        ...,
        description="Stage 1 blended composite score R(s) = 0.5 * (B(s) + sigma(s))",
    )
    evidentiary_tier: str = Field(
        ..., description="Evidentiary tier from composite score"
    )
    token_count: int = Field(..., description="Total tokens analyzed")
    window_composite_scores: list[float] | None = Field(
        default=None, description="Per-window composite scores"
    )


def compute_dna_detect_score(
    obs_logits: torch.Tensor,
    perf_logits: torch.Tensor,
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor | None = None,
) -> DNADetectResult:
    """
    Computes DNA-DetectLLM template divergence ratio sigma(s) and Stage 1 blended
    composite score R(s) = 0.5 * (B(s) + sigma(s)) using performer logits.
    """
    target_device = perf_logits.device
    if obs_logits.device != target_device:
        obs_logits = obs_logits.to(target_device)
    if input_ids.device != target_device:
        input_ids = input_ids.to(target_device)

    # Shift logits and labels for next-token prediction
    shift_perf_logits = perf_logits[:, :-1, :].contiguous()
    shift_obs_logits = obs_logits[:, :-1, :].contiguous()
    shift_labels = input_ids[:, 1:].contiguous()

    # Upcast to FP32 for numerical stability
    log_q, _ = upcast_logits_to_fp32(shift_perf_logits)
    _, p_obs = upcast_logits_to_fp32(shift_obs_logits)

    # 1. Cross-PPL: - 1/|I| sum_i sum_v p_M1(v | x_<i) * log p_M2(v | x_<i)
    token_cross_entropy = -(p_obs * log_q).sum(dim=-1)

    # 2. Greedy template tokens: max log prob under performer model
    # greedy_log_probs = log_q.max(dim=-1).values
    greedy_log_probs = log_q.max(dim=-1).values

    # 3. Performer Log-PPL on observed tokens
    gathered_log_q = torch.gather(
        log_q, dim=-1, index=shift_labels.unsqueeze(-1)
    ).squeeze(-1)

    if attention_mask is not None:
        shift_mask = attention_mask[:, 1:].to(target_device).contiguous().float()
        mask_sum = max(shift_mask.sum().item(), 1.0)
        cross_ppl = (token_cross_entropy * shift_mask).sum().item() / mask_sum
        template_nll = -(greedy_log_probs * shift_mask).sum().item() / mask_sum
        performer_log_ppl = -(gathered_log_q * shift_mask).sum().item() / mask_sum
    else:
        cross_ppl = token_cross_entropy.mean().item()
        template_nll = -greedy_log_probs.mean().item()
        performer_log_ppl = -gathered_log_q.mean().item()

    b_score = performer_log_ppl / cross_ppl if cross_ppl != 0 else 0.0
    sigma = template_nll / cross_ppl if cross_ppl != 0 else 0.0
    composite_r = 0.5 * (b_score + sigma)

    return DNADetectResult(
        binoculars_score=b_score,
        template_divergence_ratio=sigma,
        composite_score=composite_r,
        evidentiary_tier=classify_evidentiary_tier(composite_r),
        token_count=input_ids.shape[-1],
    )


class DNADetectScorer:
    """
    Secondary co-metric engine for Stage 1. Reuses performer and observer forward
    pass logits to calculate greedy ideal-AI template divergence and blended Stage 1 score.
    """

    def __init__(self, model_manager: ModelManager | None = None) -> None:
        self.model_manager = model_manager or ModelManager.get_instance()

    def compute_score_from_logits(
        self,
        obs_logits: torch.Tensor,
        perf_logits: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> DNADetectResult:
        """
        Computes DNA-DetectLLM co-metric directly from forward pass logits.
        """
        return compute_dna_detect_score(
            obs_logits=obs_logits,
            perf_logits=perf_logits,
            input_ids=input_ids,
            attention_mask=attention_mask,
        )

    def score_tokens(self, tokens: list[int]) -> DNADetectResult:
        """
        Evaluates a token sequence using sliding windows of size 512 and stride 256.
        """
        if not self.model_manager._is_loaded:
            raise RuntimeError(
                "ModelManager models are not loaded. Call load_models() first."
            )

        windows = chunk_tokens_sliding_window(tokens, window_size=512, stride=256)
        if not windows:
            return DNADetectResult(
                binoculars_score=1.0,
                template_divergence_ratio=1.0,
                composite_score=1.0,
                evidentiary_tier="T0_HUMAN",
                token_count=0,
                window_composite_scores=[],
            )

        window_scores: list[float] = []
        all_b_scores: list[float] = []
        all_sigmas: list[float] = []

        obs_model = self.model_manager.observer_model
        perf_model = self.model_manager.performer_model
        if obs_model is None or perf_model is None:
            raise RuntimeError("Observer or performer model is not loaded.")
        obs_dev = self.model_manager.observer_device
        perf_dev = self.model_manager.performer_device

        for w in windows:
            input_ids = torch.tensor([w.tokens], dtype=torch.long)
            with torch.no_grad():
                obs_out = obs_model(input_ids.to(obs_dev))
                perf_out = perf_model(input_ids.to(perf_dev))

            res = compute_dna_detect_score(
                obs_logits=obs_out.logits,
                perf_logits=perf_out.logits,
                input_ids=input_ids,
            )
            window_scores.append(res.composite_score)
            all_b_scores.append(res.binoculars_score)
            all_sigmas.append(res.template_divergence_ratio)

        avg_b = sum(all_b_scores) / len(all_b_scores)
        avg_sigma = sum(all_sigmas) / len(all_sigmas)
        final_composite = 0.5 * (avg_b + avg_sigma)

        return DNADetectResult(
            binoculars_score=avg_b,
            template_divergence_ratio=avg_sigma,
            composite_score=final_composite,
            evidentiary_tier=classify_evidentiary_tier(final_composite),
            token_count=len(tokens),
            window_composite_scores=window_scores,
        )

    def score_text(self, text: str) -> DNADetectResult:
        """
        Tokenizes text and evaluates DNA-DetectLLM blended score.
        """
        if self.model_manager.tokenizer is None:
            raise RuntimeError(
                "Tokenizer not loaded. Call model_manager.load_models() first."
            )

        tokens = self.model_manager.tokenizer.encode(text, add_special_tokens=False)
        return self.score_tokens(tokens)
