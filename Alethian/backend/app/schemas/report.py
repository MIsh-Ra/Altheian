from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from .ai_detection import AIDetectionResponse
from .match import MatchResponse, SourceResponse


class SummaryStats(BaseModel):
    total_matches: int = 0
    internal_exact: int = 0
    internal_paraphrase: int = 0
    web_matches: int = 0
    unique_sources: int = 0
    avg_match_length_words: float = 0
    longest_match_words: int = 0
    longest_match_page: int | None = None
    pages_with_matches: int = 0
    total_pages: int = 0
    excluded_matches: int = 0
    coherent_domains: list[str] = []


class HeatmapPageResponse(BaseModel):
    id: str | None = None  # Optional — not present in inline serialization
    page_number: int
    density_score: float
    match_density: float | None = None  # Frontend alias for density_score
    internal_density: float | None = None
    web_density: float | None = None
    color: str | None = None
    match_count: int | None = None
    dominant_type: str | None = None
    hotspots: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class PageDistribution(BaseModel):
    page: int
    internal_exact: int = 0
    internal_paraphrase: int = 0
    web: int = 0


class SourceBreakdownItem(BaseModel):
    name: str
    value: int


class Scores(BaseModel):
    originality_score: float
    similarity_score: float
    risk_level: str
    internal_contribution: float
    web_contribution: float


class ReviewInfo(BaseModel):
    status: str | None = "unreviewed"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    faculty_notes: str | None = None
    verdict: str | None = None


class ReportBase(BaseModel):
    score: float | None = None
    risk_level: str | None = None
    status: str = "unreviewed"


class ReportResponse(ReportBase):
    id: str
    document_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FullReportResponse(BaseModel):
    document_id: str
    document_title: str | None = None
    document_author: str | None = None
    document_text: str | None = None
    page_texts: list[dict[str, Any]] | None = []  # Per-page text with char offsets
    page_count: int | None = None
    analyzed_at: datetime
    processing_time_seconds: int | None = None

    scores: Scores
    summary_stats: SummaryStats
    source_breakdown: list[SourceBreakdownItem] = []
    sources: list[SourceResponse] = []
    matches: list[MatchResponse] = []
    heatmap: list[HeatmapPageResponse] = []
    page_distribution: list[dict[str, Any]] = []
    review: ReviewInfo
    ai_detection: AIDetectionResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ReportReviewRequest(BaseModel):
    verdict: str
    faculty_notes: str | None = None
    digital_signature: str
