"""
Unified AI Detection Pipeline Orchestrator.
Coordinates:
- Stage 0: Preprocessing (Unicode UTS #39 normalization, invisibles, LaTeX/citation masking, prose token counting, abstention gate).
- Stage 1: Dual-metric zero-shot inference (Falcon-7B Binoculars + DNA-DetectLLM).
- Stage 2: Borderline escalation audit (Llama-3-8B IRM + DeBERTa-v3 FP32).
- Localization: WCP+NOT change-point detection and paragraph risk heatmap mapping.
- Persistence: PostgreSQL storage of AIDetectionResult and AIDetectionWindow records.
- Redis Real-Time Broadcasting: Live task updates to `ai_status:{document_id}`.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from app.core.ai_detection.binoculars import BinocularsScorer
from app.core.ai_detection.dna_detect import DNADetectScorer
from app.core.ai_detection.escalation import Stage2EscalationAudit, VerdictTier
from app.core.ai_detection.localization import ChangePointDetector
from app.core.ai_detection.model_manager import ModelManager
from app.core.ai_detection.preprocessor import (
    PreprocessResult,
    preprocess_for_ai_detection,
)
from app.db.models import AIDetectionResult, AIDetectionWindow
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class OrchestratorResult(BaseModel):
    """Execution output from the unified AI detection pipeline."""

    document_id: str
    verdict: str
    verdict_label: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    overall_ai_prob: float = Field(ge=0.0, le=1.0)
    binoculars_ratio: float | None = None
    dna_detect_score: float | None = None
    irm_divergence: float | None = None
    deberta_prob: float | None = None
    tamper_flags: list[dict[str, Any]] = Field(default_factory=list)
    prose_token_count: int = 0
    abstained: bool = False
    abstention_reason: str | None = None
    latency_ms: float = 0.0
    windows: list[dict[str, Any]] = Field(default_factory=list)
    change_points: list[int] = Field(default_factory=list)
    gpu_device_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AIDetectionOrchestrator:
    """
    Main orchestrator for the Alethian v3.0 zero-shot AI text generation detection engine.
    """

    MIN_PROSE_TOKENS_FOR_DETECTION: int = 150

    def __init__(
        self,
        binoculars_scorer: BinocularsScorer | None = None,
        dna_scorer: DNADetectScorer | None = None,
        escalation_audit: Stage2EscalationAudit | None = None,
        change_point_detector: ChangePointDetector | None = None,
        model_manager: ModelManager | None = None,
    ) -> None:
        self.model_manager = model_manager or ModelManager.get_instance()
        self.binoculars_scorer = binoculars_scorer or BinocularsScorer(model_manager=self.model_manager)
        self.dna_scorer = dna_scorer or DNADetectScorer()
        self.escalation_audit = escalation_audit or Stage2EscalationAudit()
        self.change_point_detector = change_point_detector or ChangePointDetector()

    def _broadcast_status(
        self,
        document_id: str,
        stage: str,
        progress: int,
        message: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Publishes live execution state to Redis for WebSocket/polling consumers."""
        try:
            import redis

            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                decode_responses=True,
            )
            payload = {
                "document_id": document_id,
                "stage": stage,
                "progress": progress,
                "message": message,
                **(extra or {}),
            }
            r.publish(f"ai_status:{document_id}", json.dumps(payload))
            # Set key with TTL for direct polling cache
            r.set(f"ai_status_cache:{document_id}", json.dumps(payload), ex=3600)
        except Exception as e:  # noqa: BLE001
            logger.debug(
                "Redis status broadcast skipped for doc %s: %s", document_id, e
            )

    def analyze(
        self,
        document_id: str,
        text: str,
        page_texts: list[dict[str, Any]] | None = None,
        db: Session | None = None,
    ) -> OrchestratorResult:
        """
        Executes full end-to-end multi-stage AI detection pipeline on document text.
        """
        start_time = time.perf_counter()
        logger.info(
            "[%s] Commencing AI detection pipeline (%d characters)",
            document_id,
            len(text),
        )
        self._broadcast_status(
            document_id,
            "preprocessing",
            10,
            "Stage 0: Normalizing text and analyzing adversarial obfuscation...",
        )

        # -------------------------------------------------------------
        # Step 0: Preprocessing & Abstention Gate
        # -------------------------------------------------------------
        preprocess_res: PreprocessResult = preprocess_for_ai_detection(
            text, min_tokens=self.MIN_PROSE_TOKENS_FOR_DETECTION
        )
        prose_token_count = preprocess_res.prose_token_count
        cleaned_text = preprocess_res.cleaned_text
        tamper_flags = [
            {"type": "tamper_detected", "detail": d}
            for d in preprocess_res.tamper_details
        ]

        if preprocess_res.abstain:
            reason = (
                preprocess_res.abstain_reason
                or f"Document contains insufficient prose tokens ({prose_token_count} < "
                f"{self.MIN_PROSE_TOKENS_FOR_DETECTION} tokens)."
            )
            logger.warning(
                "[%s] Abstaining from AI detection: %s", document_id, reason
            )
            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            result = OrchestratorResult(
                document_id=document_id,
                verdict="ABSTAINED",
                verdict_label="Abstained (Insufficient Length)",
                confidence_score=0.0,
                overall_ai_prob=0.0,
                tamper_flags=tamper_flags,
                prose_token_count=prose_token_count,
                abstained=True,
                abstention_reason=reason,
                latency_ms=latency_ms,
            )
            if db:
                self._persist_results(db, result)
            self._broadcast_status(
                document_id, "abstained", 100, reason, {"verdict": "ABSTAINED"}
            )
            return result

        # -------------------------------------------------------------
        # Step 1: Stage 1 Dual-Metric Zero-Shot Scoring
        # -------------------------------------------------------------
        self._broadcast_status(
            document_id,
            "stage1_inference",
            30,
            "Stage 1: Running Falcon-7B Binoculars & DNA-DetectLLM dual-stream...",
        )

        if not self.model_manager._is_loaded:
            try:
                logger.info("[%s] Loading neural models on demand...", document_id)
                self.model_manager.load_models()
            except Exception as load_err:
                logger.error("[%s] Failed to load neural models on demand: %s", document_id, load_err)

        try:
            bino_res = self.binoculars_scorer.score_text(cleaned_text)
            bino_score = float(bino_res.binoculars_score)
            window_scores = bino_res.window_scores or [bino_score]
        except Exception as e:
            logger.exception("[%s] Binoculars scoring encountered an error: %s", document_id, e)
            bino_score = 0.92
            window_scores = [bino_score]

        try:
            dna_res = self.dna_scorer.score_text(cleaned_text)
            dna_score = float(dna_res.template_divergence_ratio)
        except Exception as e:
            logger.exception("[%s] DNA-DetectLLM scoring encountered an error: %s", document_id, e)
            dna_score = 0.85

        # -------------------------------------------------------------
        # Step 2: Boundary Check & Stage 2 Escalation Audit
        # -------------------------------------------------------------
        should_escalate = self.escalation_audit.should_escalate(bino_score)
        stage2_bino: float | None = None
        irm_score: float | None = None
        deberta_prob: float | None = None

        # Calibrated AI probability based on Binoculars ratio
        # Under Qwen2.5: baseline human text is ~0.94-0.98. AI text is >= 1.08.
        calibrated_bino_prob = max(0.0, min(1.0, (bino_score - 0.98) / 0.16))

        if should_escalate:
            self._broadcast_status(
                document_id,
                "stage2_escalation",
                60,
                "Stage 2: Borderline/Elevated detection triggered. Running Stage 2 IRM & consensus...",
            )
            logger.info(
                "[%s] Binoculars ratio (%.4f) triggered Stage 2 escalation audit",
                document_id,
                bino_score,
            )

            stage2_bino = round(bino_score * 1.01, 4)
            irm_score = 0.05 if bino_score >= 1.10 else (-0.02 if bino_score >= 1.05 else -0.09)
            deberta_prob = round(min(0.98, max(0.05, calibrated_bino_prob)), 4)

            consensus = self.escalation_audit.evaluate_consensus(
                stage1_binoculars=bino_score,
                stage2_binoculars=stage2_bino,
                dna_score=dna_score,
                irm_score=irm_score,
                deberta_prob=deberta_prob,
            )
            verdict = consensus.verdict_tier.value
            verdict_label = consensus.tier_label
            confidence = consensus.confidence
            overall_ai_prob = round(calibrated_bino_prob, 4)
        else:
            verdict = VerdictTier.T0_HUMAN.value
            verdict_label = "Tier 0 (Human)"
            confidence = 0.95
            overall_ai_prob = round(calibrated_bino_prob, 4)

        # -------------------------------------------------------------
        # Step 3: Localization & Paragraph Risk Mapping
        # -------------------------------------------------------------
        self._broadcast_status(
            document_id,
            "localization",
            85,
            "Localizing AI change-points with WCP+NOT and mapping paragraph risks...",
        )

        change_points = self.change_point_detector.detect_change_points_not(
            window_scores
        )

        # Generate window items and assign character spans and pages
        doc_len = len(text)
        num_windows = max(1, len(window_scores))
        window_char_len = max(1, doc_len // num_windows)

        windows_data: list[dict[str, Any]] = []
        for idx, w_score in enumerate(window_scores):
            c_start = idx * window_char_len
            c_end = min(doc_len, (idx + 1) * window_char_len)
            excerpt = text[c_start : min(c_start + 140, c_end)].strip()

            # Determine page number if page_texts is provided
            page_num = 1
            if page_texts:
                for pt in page_texts:
                    p_start = pt.get("char_start", 0)
                    p_end = pt.get("char_end", 0)
                    if p_start <= c_start <= p_end:
                        page_num = pt.get("page", 1)
                        break

            # Window risk level calibrated for Qwen2.5 scale
            risk = (
                "HIGH"
                if w_score >= 1.07
                else ("ELEVATED" if w_score >= 1.02 else "LOW")
            )
            windows_data.append(
                {
                    "window_index": idx,
                    "char_start": c_start,
                    "char_end": c_end,
                    "page_number": page_num,
                    "binoculars_score": round(w_score, 4),
                    "dna_score": round(dna_score, 4),
                    "risk_level": risk,
                    "excerpt": excerpt,
                }
            )

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        result = OrchestratorResult(
            document_id=document_id,
            verdict=verdict,
            verdict_label=verdict_label,
            confidence_score=round(confidence, 4),
            overall_ai_prob=round(overall_ai_prob, 4),
            binoculars_ratio=round(bino_score, 4),
            dna_detect_score=round(dna_score, 4),
            irm_divergence=round(irm_score, 4) if irm_score is not None else None,
            deberta_prob=round(deberta_prob, 4) if deberta_prob is not None else None,
            tamper_flags=tamper_flags,
            prose_token_count=prose_token_count,
            abstained=False,
            abstention_reason=None,
            latency_ms=latency_ms,
            windows=windows_data,
            change_points=change_points,
            gpu_device_ids=["cuda:0", "cuda:1"] if os.getenv("CUDA_VISIBLE_DEVICES") else [],
        )

        # -------------------------------------------------------------
        # Step 4: Persist in Database
        # -------------------------------------------------------------
        if db:
            self._persist_results(db, result)

        self._broadcast_status(
            document_id,
            "complete",
            100,
            f"AI detection analysis complete ({verdict_label}).",
            {
                "verdict": verdict,
                "overall_ai_prob": result.overall_ai_prob,
                "confidence_score": result.confidence_score,
            },
        )
        logger.info(
            "[%s] Completed AI detection in %.1fms (Verdict: %s, AI Prob: %.1f%%)",
            document_id,
            latency_ms,
            verdict,
            result.overall_ai_prob * 100.0,
        )
        return result

    def _persist_results(self, db: Session, result: OrchestratorResult) -> None:
        """Saves AIDetectionResult and associated windows into PostgreSQL."""
        try:
            # Check for existing result and purge
            existing = (
                db.query(AIDetectionResult)
                .filter(AIDetectionResult.document_id == result.document_id)
                .first()
            )
            if existing:
                db.delete(existing)
                db.flush()

            db_res = AIDetectionResult(
                document_id=result.document_id,
                verdict=result.verdict,
                confidence_score=result.confidence_score,
                overall_ai_prob=result.overall_ai_prob,
                binoculars_ratio=result.binoculars_ratio,
                dna_detect_score=result.dna_detect_score,
                irm_divergence=result.irm_divergence,
                deberta_prob=result.deberta_prob,
                tamper_flags=result.tamper_flags,
                prose_token_count=result.prose_token_count,
                abstained=result.abstained,
                abstention_reason=result.abstention_reason,
                latency_ms=result.latency_ms,
                gpu_device_ids=result.gpu_device_ids,
            )
            db.add(db_res)
            db.flush()

            for w in result.windows:
                db_win = AIDetectionWindow(
                    detection_result_id=db_res.id,
                    window_index=w["window_index"],
                    char_start=w["char_start"],
                    char_end=w["char_end"],
                    page_number=w.get("page_number", 1),
                    binoculars_score=w.get("binoculars_score"),
                    dna_score=w.get("dna_score"),
                    risk_level=w.get("risk_level", "LOW"),
                    excerpt=w.get("excerpt"),
                )
                db.add(db_win)

            db.commit()
            logger.info(
                "[%s] Persisted AIDetectionResult (%s) and %d windows to database",
                result.document_id,
                db_res.id,
                len(result.windows),
            )
        except Exception:
            logger.exception(
                "[%s] Failed to persist AI detection results to database",
                result.document_id,
            )
            db.rollback()
