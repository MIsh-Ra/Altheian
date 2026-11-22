"""
Stage 1 Binoculars scoring engine for zero-shot AI text detection.
Computes dual-stream forward passes, transfers logits across NVLink, upcasts to FP32,
and calculates Performer Log-PPL and Observer-Performer Cross-PPL ratios.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import torch
import torch.nn.functional as F
from pydantic import BaseModel, Field

from .model_manager import ModelManager

logger = logging.getLogger(__name__)


class WindowChunk(BaseModel):
    """Represents a chunk of tokens for sliding-window inference."""

    window_idx: int
    start_idx: int
    end_idx: int
    tokens: list[int]
    warmup_discard: int = 0


class BinocularsResult(BaseModel):
    """Structured output for Binoculars score evaluation."""

    performer_log_ppl: float = Field(
        ..., description="Performer model Log-PPL (numerator)"
    )
    cross_ppl: float = Field(
        ..., description="Observer-Performer Cross-PPL (denominator)"
    )
    binoculars_score: float = Field(
        ..., description="Ratio of performer log-ppl to cross-ppl"
    )
    evidentiary_tier: str = Field(..., description="Evidentiary classification tier")
    token_count: int = Field(..., description="Total tokens analyzed")
    window_scores: list[float] | None = Field(
        default=None, description="Per-window Binoculars scores"
    )


def classify_evidentiary_tier(score: float) -> str:
    """
    Classifies a Binoculars score into standard evidentiary tiers:
    - score >= 0.9015 -> 'T0_HUMAN' (Statistically consistent with human authorship)
    - 0.8536 <= score < 0.9015 -> 'T1_INDETERMINATE' (Indeterminate human/AI overlap zone)
    - score < 0.8536 -> 'ESCALATE' (Elevated AI signal requiring Stage 2 audit)
    """
    if score >= 0.9015:
        return "T0_HUMAN"
    elif score >= 0.8536:
        return "T1_INDETERMINATE"
    else:
        return "ESCALATE"


def upcast_logits_to_fp32(logits: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Casts logits to float32 before computing F.log_softmax and F.softmax,
    eliminating FP16 overflow/saturation at 65,504 and guaranteeing zero NaNs or Infs.

    Args:
        logits: Tensor of shape (..., vocab_size), typically in torch.float16.

    Returns:
        Tuple of (log_probs, probs) strictly in torch.float32.
    """
    logits_fp32 = logits.float()
    log_probs = F.log_softmax(logits_fp32, dim=-1)
    probs = F.softmax(logits_fp32, dim=-1)
    return log_probs, probs


def chunk_tokens_sliding_window(
    token_sequence: Sequence[int],
    window_size: int = 512,
    stride: int = 256,
) -> list[WindowChunk]:
    """
    Partitions a token sequence into 512-token windows with stride 256 (50% overlap).
    For non-initial windows (window_idx > 0), marks warmup_discard=128 to ensure
    all scored tokens have at least 256–512 tokens of prior context.
    """
    total = len(token_sequence)
    if total == 0:
        return []
    if total <= window_size:
        return [
            WindowChunk(
                window_idx=0,
                start_idx=0,
                end_idx=total,
                tokens=list(token_sequence),
                warmup_discard=0,
            )
        ]

    windows: list[WindowChunk] = []
    window_idx = 0
    start = 0

    while start < total:
        end = min(start + window_size, total)
        warmup = 0 if window_idx == 0 else 128
        windows.append(
            WindowChunk(
                window_idx=window_idx,
                start_idx=start,
                end_idx=end,
                tokens=list(token_sequence[start:end]),
                warmup_discard=warmup,
            )
        )
        if end >= total:
            break
        start += stride
        window_idx += 1

    return windows


def stitch_sliding_window_scores(
    windows: list[WindowChunk],
    window_per_token_scores: list[list[float]],
    warmup_tokens: int = 128,
) -> list[float]:
    """
    Stitches per-token window scores across the entire sequence.
    Discards the first `warmup_tokens` for non-initial windows (window_idx > 0).
    Averages overlapping predictions across stitched regions.
    """
    if not windows:
        return []
    total_tokens = max(w.end_idx for w in windows)
    token_accum: list[list[float]] = [[] for _ in range(total_tokens)]

    for w, scores in zip(windows, window_per_token_scores):
        warmup = w.warmup_discard if w.window_idx > 0 else 0
        for local_idx in range(warmup, len(scores)):
            doc_idx = w.start_idx + local_idx
            if doc_idx < total_tokens:
                token_accum[doc_idx].append(scores[local_idx])

    result: list[float] = []
    last_val = 0.0
    for vals in token_accum:
        if vals:
            last_val = sum(vals) / len(vals)
            result.append(last_val)
        else:
            result.append(last_val)
    return result


def compute_binoculars_ratio(
    obs_logits: torch.Tensor,
    perf_logits: torch.Tensor,
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor | None = None,
) -> tuple[float, float, float]:
    """
    Computes Performer Log-PPL, Observer-Performer Cross-PPL, and Binoculars score
    from observer and performer causal logits.

    Returns:
        (performer_log_ppl, cross_ppl, binoculars_ratio)
    """
    # Transfer observer logits to performer device across NVLink if needed
    target_device = perf_logits.device
    if obs_logits.device != target_device:
        obs_logits = obs_logits.to(target_device)
    if input_ids.device != target_device:
        input_ids = input_ids.to(target_device)

    # Shift logits and labels for autoregressive next-token prediction
    shift_perf_logits = perf_logits[:, :-1, :].contiguous()
    shift_obs_logits = obs_logits[:, :-1, :].contiguous()
    shift_labels = input_ids[:, 1:].contiguous()

    # Upcast to FP32 for numerical stability
    log_q, _ = upcast_logits_to_fp32(shift_perf_logits)
    _, p_obs = upcast_logits_to_fp32(shift_obs_logits)

    # Performer Log-PPL: - 1/|I| sum log P_M2(x_i | x_<i)
    gathered_log_q = torch.gather(
        log_q, dim=-1, index=shift_labels.unsqueeze(-1)
    ).squeeze(-1)

    # Cross-PPL: - 1/|I| sum_i sum_v p_M1(v | x_<i) * log p_M2(v | x_<i)
    token_cross_entropy = -(p_obs * log_q).sum(dim=-1)

    if attention_mask is not None:
        shift_mask = attention_mask[:, 1:].to(target_device).contiguous().float()
        mask_sum = max(shift_mask.sum().item(), 1.0)
        performer_log_ppl = -(gathered_log_q * shift_mask).sum().item() / mask_sum
        cross_ppl = (token_cross_entropy * shift_mask).sum().item() / mask_sum
    else:
        performer_log_ppl = -gathered_log_q.mean().item()
        cross_ppl = token_cross_entropy.mean().item()

    binoculars_ratio = performer_log_ppl / cross_ppl if cross_ppl != 0 else 0.0
    return performer_log_ppl, cross_ppl, binoculars_ratio


class BinocularsScorer:
    """
    Dual-stream zero-shot AI text detector utilizing the Binoculars metric
    with Falcon-7B (Observer) and Falcon-7B-Instruct (Performer).
    """

    def __init__(self, model_manager: ModelManager | None = None) -> None:
        self.model_manager = model_manager or ModelManager.get_instance()

    def compute_score_from_logits(
        self,
        obs_logits: torch.Tensor,
        perf_logits: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> BinocularsResult:
        """
        Computes Binoculars metrics directly from precomputed logits.
        """
        ppl, xppl, ratio = compute_binoculars_ratio(
            obs_logits=obs_logits,
            perf_logits=perf_logits,
            input_ids=input_ids,
            attention_mask=attention_mask,
        )
        tier = classify_evidentiary_tier(ratio)
        token_count = input_ids.shape[-1]

        return BinocularsResult(
            performer_log_ppl=ppl,
            cross_ppl=xppl,
            binoculars_score=ratio,
            evidentiary_tier=tier,
            token_count=token_count,
        )

    def score_tokens(self, tokens: list[int]) -> BinocularsResult:
        """
        Evaluates a token sequence using sliding windows of size 512 and stride 256.
        """
        if not self.model_manager._is_loaded:
            raise RuntimeError(
                "ModelManager models are not loaded. Call load_models() first."
            )

        windows = chunk_tokens_sliding_window(tokens, window_size=512, stride=256)
        if not windows:
            return BinocularsResult(
                performer_log_ppl=0.0,
                cross_ppl=0.0,
                binoculars_score=1.0,
                evidentiary_tier="T0_HUMAN",
                token_count=0,
                window_scores=[],
            )

        window_scores: list[float] = []
        all_ppl: list[float] = []
        all_xppl: list[float] = []

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

            ppl, xppl, ratio = compute_binoculars_ratio(
                obs_logits=obs_out.logits,
                perf_logits=perf_out.logits,
                input_ids=input_ids,
            )
            window_scores.append(ratio)
            all_ppl.append(ppl)
            all_xppl.append(xppl)

        avg_ppl = sum(all_ppl) / len(all_ppl)
        avg_xppl = sum(all_xppl) / len(all_xppl)
        final_score = avg_ppl / avg_xppl if avg_xppl != 0 else 0.0

        return BinocularsResult(
            performer_log_ppl=avg_ppl,
            cross_ppl=avg_xppl,
            binoculars_score=final_score,
            evidentiary_tier=classify_evidentiary_tier(final_score),
            token_count=len(tokens),
            window_scores=window_scores,
        )

    def score_text(self, text: str) -> BinocularsResult:
        """
        Tokenizes text and evaluates Binoculars score.
        """
        if self.model_manager.tokenizer is None:
            raise RuntimeError(
                "Tokenizer not loaded. Call model_manager.load_models() first."
            )

        tokens = self.model_manager.tokenizer.encode(text, add_special_tokens=False)
        return self.score_tokens(tokens)
