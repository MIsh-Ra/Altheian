"""
Stage 2 Escalation Audit:
- Llama-3-8B Binoculars + DNA-DetectLLM frontier confirmation.
- Implicit Reward Model (IRM): Length-normalized DPO log-policy ratio.
- DeBERTa-v3 Academic Classifier: desklib/ai-text-detector-academic-v1.01 in native FP32.
- Multi-metric consensus decision logic resolving into standard evidentiary tiers:
    * Tier 0 (Human)
    * Tier 1 (Inconclusive)
    * Tier 2 (Mixed AI)
    * Tier 3 (Elevated AI)
"""

from enum import Enum
from typing import Any

import torch
from pydantic import BaseModel, Field
from torch import nn


class VerdictTier(str, Enum):
    """Standard academic integrity due-process evidentiary tiers."""

    T0_HUMAN = "T0_HUMAN"
    T1_INDETERMINATE = "T1_INDETERMINATE"
    T2_ELEVATED = "T2_ELEVATED"
    T3_HIGH = "T3_HIGH"


class ConsensusResult(BaseModel):
    """Structured result of multi-metric consensus evaluation."""

    verdict_tier: VerdictTier
    tier_label: str
    confidence: float = Field(ge=0.0, le=1.0)
    flags: dict[str, bool]
    reasoning: str
    metrics: dict[str, float | None]


class Stage2EscalationAudit:
    """
    Stage 2 Escalation Engine for borderline or indeterminate submissions.
    Combines frontier Llama-3-8B pair (Binoculars + DNA + IRM) with FP32 DeBERTa-v3.
    """

    # Threshold constants per v3.0 specification
    ESCALATION_TRIGGER_THRESHOLD: float = (
        0.8536  # Stage 1 Score < 0.8536 triggers Stage 2
    )
    T0_HUMAN_THRESHOLD: float = 0.9015
    T2_MIXED_THRESHOLD: float = 0.8536
    T3_HIGH_THRESHOLD: float = 0.8350
    DNA_AI_THRESHOLD: float = 0.7500
    IRM_AI_THRESHOLD: float = 0.1500
    DEBERTA_AI_THRESHOLD: float = 0.5000
    DEBERTA_HIGH_AI_THRESHOLD: float = 0.8000

    # Model identifiers
    LLAMA_BASE_MODEL: str = "meta-llama/Meta-Llama-3-8B"
    LLAMA_INSTRUCT_MODEL: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    DEBERTA_MODEL_NAME: str = "desklib/ai-text-detector-academic-v1.01"

    def should_escalate(self, stage1_binoculars: float) -> bool:
        """
        Determines whether a document or section requires Stage 2 escalation.
        Only borderline / indeterminate submissions (< 0.8536) escalate.
        """
        return stage1_binoculars < self.ESCALATION_TRIGGER_THRESHOLD

    def compute_irm_ratio(
        self,
        log_probs_instruct: torch.Tensor,
        log_probs_base: torch.Tensor,
    ) -> float:
        """
        Computes the length-normalized Implicit Reward Model (IRM) DPO log-policy ratio:
            r_IRM(s) = (1 / |I|) * sum_{i in I} log(P_pi(x_i | x_<i) / P_ref(x_i | x_<i))
                     = (1 / |I|) * sum_{i in I} [log P_pi(x_i | x_<i) - log P_ref(x_i | x_<i)]

        Measures instruction-tuning preference alignment signal.
        Positive elevated values indicate strong AI alignment preference.
        """
        if log_probs_instruct.numel() == 0 or log_probs_base.numel() == 0:
            return 0.0

        p_instruct_f32 = log_probs_instruct.detach().float()
        p_base_f32 = log_probs_base.detach().float()

        delta = p_instruct_f32 - p_base_f32
        return float(torch.mean(delta).item())

    def compute_irm_from_logits(
        self,
        instruct_logits: torch.Tensor,
        base_logits: torch.Tensor,
        input_ids: torch.Tensor,
    ) -> float:
        """
        Extracts target token log probabilities from model logits in float32
        and returns the length-normalized DPO log-policy ratio.
        """
        # Ensure FP32 precision to prevent vocabulary overflow
        instruct_logits_f32 = instruct_logits.detach().float()
        base_logits_f32 = base_logits.detach().float()

        # Shift tokens for next-token prediction
        # input_ids: (batch, seq_len)
        if input_ids.dim() == 1:
            input_ids = input_ids.unsqueeze(0)
        if instruct_logits_f32.dim() == 2:
            instruct_logits_f32 = instruct_logits_f32.unsqueeze(0)
        if base_logits_f32.dim() == 2:
            base_logits_f32 = base_logits_f32.unsqueeze(0)

        targets = input_ids[:, 1:].contiguous()
        logits_inst_shift = instruct_logits_f32[:, :-1, :].contiguous()
        logits_base_shift = base_logits_f32[:, :-1, :].contiguous()

        # Compute log softmax over vocabulary
        log_probs_inst = torch.log_softmax(logits_inst_shift, dim=-1)
        log_probs_base = torch.log_softmax(logits_base_shift, dim=-1)

        # Gather target token log probabilities
        inst_target_logp = log_probs_inst.gather(
            dim=-1, index=targets.unsqueeze(-1)
        ).squeeze(-1)
        base_target_logp = log_probs_base.gather(
            dim=-1, index=targets.unsqueeze(-1)
        ).squeeze(-1)

        return self.compute_irm_ratio(inst_target_logp, base_target_logp)

    def predict_deberta_from_logits(self, logits: Any) -> dict[str, Any]:
        """
        Converts classification logits to softmax probabilities strictly in float32.
        Guarantees protection against DeBERTa-v3 FP16 numerical collapse.
        """
        if not isinstance(logits, torch.Tensor):
            logits_f32 = torch.tensor(logits, dtype=torch.float32)
        else:
            logits_f32 = logits.detach().float()

        probs = torch.softmax(logits_f32, dim=-1)

        # Assuming standard binary classification: class 0 = Human, class 1 = AI
        if probs.shape[-1] >= 2:
            p_human = float(probs[0, 0].item())
            p_ai = float(probs[0, 1].item())
        else:
            p_ai = float(torch.sigmoid(logits_f32).item())
            p_human = 1.0 - p_ai

        return {
            "ai_probability": p_ai,
            "human_probability": p_human,
            "dtype": "torch.float32",
            "logits": logits_f32.cpu().tolist(),
        }

    def run_deberta_inference(
        self,
        model: Any,
        tokenizer: Any,
        text: str,
        device: str = "cpu",
    ) -> dict[str, Any]:
        """
        Executes DeBERTa-v3 academic classifier strictly in torch.float32.
        """
        # Ensure PyTorch model operates in FP32
        if isinstance(model, nn.Module):
            model = model.to(dtype=torch.float32, device=device)
            model.eval()
        eval_fn = getattr(model, "eval", None)
        if callable(eval_fn):
            try:
                eval_fn()
            except (RuntimeError, AttributeError):
                pass

        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )

        if isinstance(inputs, dict):
            device_inputs = {}
            for k, v in inputs.items():
                if isinstance(v, torch.Tensor):
                    device_inputs[k] = v.to(device)
                else:
                    device_inputs[k] = v
            inputs = device_inputs

        with torch.no_grad():
            outputs = model(**inputs)
            if hasattr(outputs, "logits"):
                logits = outputs.logits
            elif isinstance(outputs, dict) and "logits" in outputs:
                logits = outputs["logits"]
            else:
                logits = outputs

            if isinstance(logits, torch.Tensor):
                logits = logits.float()

        return self.predict_deberta_from_logits(logits)

    def evaluate_consensus(
        self,
        stage1_binoculars: float,
        stage2_binoculars: float | None = None,
        dna_score: float | None = None,
        irm_score: float | None = None,
        deberta_prob: float | None = None,
    ) -> ConsensusResult:
        """
        Synthesizes multi-metric consensus across:
        1. Binoculars (Falcon-7B Stage 1 and/or Llama-3-8B Stage 2)
        2. DNA-DetectLLM (Template divergence ratio)
        3. Implicit Reward Model (Length-normalized DPO log-policy ratio)
        4. DeBERTa-v3 Academic Classifier (FP32 auxiliary probability)

        Resolves into standard due-process evidentiary tiers:
        - Tier 0: T0_HUMAN ("Tier 0 (Human)")
        - Tier 1: T1_INDETERMINATE ("Tier 1 (Inconclusive)")
        - Tier 2: T2_ELEVATED ("Tier 2 (Mixed AI)")
        - Tier 3: T3_HIGH ("Tier 3 (Elevated AI)")
        """
        effective_bino = (
            stage2_binoculars if stage2_binoculars is not None else stage1_binoculars
        )

        # Evaluate individual metric flags
        bino_ai = effective_bino < self.T3_HIGH_THRESHOLD
        bino_mixed = self.T3_HIGH_THRESHOLD <= effective_bino < self.T2_MIXED_THRESHOLD
        bino_human = effective_bino >= self.T0_HUMAN_THRESHOLD

        dna_ai = dna_score is not None and dna_score < self.DNA_AI_THRESHOLD
        irm_ai = irm_score is not None and irm_score > self.IRM_AI_THRESHOLD
        deberta_ai = (
            deberta_prob is not None and deberta_prob >= self.DEBERTA_AI_THRESHOLD
        )
        deberta_strong_ai = (
            deberta_prob is not None and deberta_prob >= self.DEBERTA_HIGH_AI_THRESHOLD
        )
        deberta_human = (
            deberta_prob is not None and deberta_prob < self.DEBERTA_AI_THRESHOLD
        )

        flags = {
            "binoculars_ai": bool(effective_bino < self.T2_MIXED_THRESHOLD),
            "dna_ai": bool(dna_ai),
            "irm_ai": bool(irm_ai),
            "deberta_ai": bool(deberta_ai),
        }

        # Count corroborating AI indicators
        active_ai_signals = sum(
            [
                effective_bino < self.T2_MIXED_THRESHOLD,
                dna_ai,
                irm_ai,
                deberta_ai,
            ]
        )

        metrics_dict: dict[str, float | None] = {
            "stage1_binoculars": stage1_binoculars,
            "stage2_binoculars": stage2_binoculars,
            "dna_score": dna_score,
            "irm_score": irm_score,
            "deberta_prob": deberta_prob,
        }

        # Decision Logic:
        # Tier 0: Clean Human
        if (
            bino_human
            and (deberta_prob is None or deberta_human)
            and not (dna_ai and irm_ai)
        ):
            return ConsensusResult(
                verdict_tier=VerdictTier.T0_HUMAN,
                tier_label="Tier 0 (Human)",
                confidence=0.95 if deberta_human else 0.90,
                flags=flags,
                reasoning=(
                    f"Perplexity-cross-perplexity ratio ({effective_bino:.4f}) is statistically "
                    "consistent with human authorship across dual-model benchmarks."
                ),
                metrics=metrics_dict,
            )

        # Tier 3: Elevated AI (3+ metrics flag AI, or strong Binoculars + strong DeBERTa)
        if (bino_ai and (deberta_strong_ai or (dna_ai and irm_ai))) or (
            active_ai_signals >= 3 and (deberta_prob is None or deberta_strong_ai)
        ):
            conf = 0.96 if deberta_strong_ai else 0.90
            return ConsensusResult(
                verdict_tier=VerdictTier.T3_HIGH,
                tier_label="Tier 3 (Elevated AI)",
                confidence=conf,
                flags=flags,
                reasoning=(
                    f"Strong statistical AI generation signal confirmed across {active_ai_signals} "
                    f"independent models (Binoculars={effective_bino:.4f}, DeBERTa={deberta_prob or 0.0:.2f}, "
                    f"IRM={irm_score or 0.0:.2f})."
                ),
                metrics=metrics_dict,
            )

        # Tier 2: Mixed / Partially AI (2+ metrics flag AI or borderline score corroborated)
        if (
            active_ai_signals >= 2
            or (bino_mixed and (deberta_ai or irm_ai or dna_ai))
            or (deberta_ai and (dna_ai or irm_ai))
        ):
            return ConsensusResult(
                verdict_tier=VerdictTier.T2_ELEVATED,
                tier_label="Tier 2 (Mixed AI)",
                confidence=0.82,
                flags=flags,
                reasoning=(
                    f"Elevated AI signal corroborated by Stage 2 escalation ({active_ai_signals} metrics flagged). "
                    "Recommend localized inspection of highlighted paragraphs."
                ),
                metrics=metrics_dict,
            )

        # Tier 1: Indeterminate Human/AI overlap
        return ConsensusResult(
            verdict_tier=VerdictTier.T1_INDETERMINATE,
            tier_label="Tier 1 (Inconclusive)",
            confidence=0.60,
            flags=flags,
            reasoning=(
                f"Borderline score ({effective_bino:.4f}) without decisive multi-metric consensus. "
                "Inconclusive evidentiary threshold; no disciplinary inference warranted."
            ),
            metrics=metrics_dict,
        )
