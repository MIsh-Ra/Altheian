from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AIDetectionWindowSchema(BaseModel):
    """Schema for individual sliding-window or paragraph-level AI risk scoring."""

    id: str | None = None
    window_index: int
    char_start: int
    char_end: int
    page_number: int = 1
    binoculars_score: float | None = None
    dna_score: float | None = None
    risk_level: str = Field(default="LOW", description="LOW, ELEVATED, or HIGH risk")
    excerpt: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TamperEventSchema(BaseModel):
    """Schema for detected adversarial Unicode or obfuscation events."""

    type: str
    char_offset: int | None = None
    codepoint: str | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AIDetectionResponse(BaseModel):
    """Unified API response for AI text generation detection analysis."""

    id: str
    document_id: str
    verdict: str = Field(
        ...,
        description="Evidentiary tier: T0_HUMAN, T1_INDETERMINATE, T2_ELEVATED, T3_HIGH, or ABSTAINED",
    )
    verdict_label: str | None = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    overall_ai_prob: float = Field(ge=0.0, le=1.0)
    binoculars_ratio: float | None = None
    dna_detect_score: float | None = None
    irm_divergence: float | None = None
    deberta_prob: float | None = None
    tamper_flags: list[dict[str, Any]] | None = None
    prose_token_count: int = 0
    abstained: bool = False
    abstention_reason: str | None = None
    latency_ms: float = 0.0
    gpu_device_ids: list[str] | None = None
    windows: list[AIDetectionWindowSchema] = []
    change_points: list[int] | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIDetectionStatusResponse(BaseModel):
    """Real-time polling status for AI text generation detection job."""

    document_id: str
    status: str = Field(
        ...,
        description="Current pipeline status: pending, processing, analyzing_stage1, escalating_stage2, complete, or failed",
    )
    progress: int = Field(default=0, ge=0, le=100)
    message: str | None = None
    has_result: bool = False

    model_config = ConfigDict(from_attributes=True)
