from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import declarative_base, relationship

try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    from sqlalchemy import JSON as JSONB
import datetime
import enum
import uuid

Base = declarative_base()


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    ingesting = "ingesting"
    analyzing = "analyzing"
    processing = "processing"
    complete = "complete"
    failed = "failed"
    error = "error"


class UserRole(str, enum.Enum):
    admin = "admin"
    faculty = "faculty"
    student = "student"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.faculty)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=True)
    author = Column(String, nullable=True)
    filename = Column(String, nullable=False)
    upload_date = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    status = Column(Enum(DocumentStatus), default=DocumentStatus.pending)
    meta_data = Column(JSON, nullable=True)
    content = Column(String, nullable=True)

    # Phase 0: Archive Integration
    archive_metadata = Column(JSONB, nullable=True)

    # Phase 1: New properties
    course_id = Column(String, nullable=True)
    is_archived = Column(Boolean, default=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)

    page_count = Column(Integer, nullable=True)
    risk_level = Column(String, nullable=True)
    originality_score = Column(Float, nullable=True)
    # Stores [{page: int, text: str, char_start: int, char_end: int}, ...] for page-aware rendering
    page_texts = Column(JSON, nullable=True)

    user = relationship("User", backref="documents")
    ai_detection_result = relationship(
        "AIDetectionResult", back_populates="document", uselist=False
    )


class Report(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"))
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    doc_word_count = Column(
        Integer, nullable=True
    )  # Actual word count for consistent recalculation
    risk_level = Column(String, nullable=True)
    status = Column(String, default="unreviewed")
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    faculty_notes = Column(String, nullable=True)
    verdict = Column(String, nullable=True)
    processing_time_seconds = Column(Integer, nullable=True)
    digital_signature = Column(String, nullable=True)

    document = relationship("Document", backref="report")
    matches = relationship("Match", back_populates="report")
    heatmap_pages = relationship("HeatmapPage", back_populates="report")
    reviewer = relationship("User")


class Source(Base):
    __tablename__ = "sources"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(String, nullable=True)
    title = Column(String, nullable=True)
    author = Column(String, nullable=True)

    type = Column(String, nullable=True)
    domain = Column(String, nullable=True)
    document_id = Column(
        String, ForeignKey("documents.id"), nullable=True
    )  # The MATCHED source document (internal) or NULL (web)
    report_document_id = Column(
        String, ForeignKey("documents.id"), nullable=True
    )  # The analyzed (submitted) document
    coverage_percent = Column(Float, nullable=True)
    match_count = Column(Integer, nullable=True)
    pages_affected = Column(JSON, nullable=True)
    is_coherent_source = Column(Boolean, default=False)


class Match(Base):
    __tablename__ = "matches"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String, ForeignKey("reports.id"))
    source_id = Column(String, ForeignKey("sources.id"), nullable=True)
    submitted_text = Column(String)
    source_text = Column(String)
    similarity = Column(Float)
    is_excluded = Column(Boolean, default=False)
    comment = Column(String, nullable=True)

    type = Column(String, nullable=True)
    submitted_page = Column(Integer, nullable=True)
    source_page = Column(Integer, nullable=True)
    submitted_start_char = Column(Integer, nullable=True)
    submitted_end_char = Column(Integer, nullable=True)
    match_length_words = Column(Integer, nullable=True)
    exclude_reason = Column(String, nullable=True)
    color_code = Column(String, nullable=True)

    report = relationship("Report", back_populates="matches")
    source = relationship("Source")


class HeatmapPage(Base):
    __tablename__ = "heatmap_pages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String, ForeignKey("reports.id"))
    page_number = Column(Integer)
    density_score = Column(Float)
    hotspots = Column(JSON, nullable=True)

    internal_density = Column(Float, nullable=True)
    web_density = Column(Float, nullable=True)
    color = Column(String, nullable=True)
    match_count = Column(Integer, nullable=True)
    dominant_type = Column(String, nullable=True)

    report = relationship("Report", back_populates="heatmap_pages")


class AIDetectionResult(Base):
    __tablename__ = "ai_detection_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String, ForeignKey("documents.id"), unique=True, index=True, nullable=False
    )
    verdict = Column(
        String, nullable=False
    )  # "T0_HUMAN", "T1_INDETERMINATE", "T2_ELEVATED", "T3_HIGH", "ABSTAINED"
    confidence_score = Column(Float, nullable=False, default=0.0)
    overall_ai_prob = Column(Float, nullable=False, default=0.0)
    binoculars_ratio = Column(Float, nullable=True)
    dna_detect_score = Column(Float, nullable=True)
    irm_divergence = Column(Float, nullable=True)
    deberta_prob = Column(Float, nullable=True)
    tamper_flags = Column(JSON, nullable=True)  # List of detected tamper events
    prose_token_count = Column(Integer, default=0)
    abstained = Column(Boolean, default=False)
    abstention_reason = Column(String, nullable=True)
    latency_ms = Column(Float, default=0.0)
    gpu_device_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))

    document = relationship("Document", back_populates="ai_detection_result")
    windows = relationship(
        "AIDetectionWindow",
        back_populates="detection_result",
        cascade="all, delete-orphan",
    )


class AIDetectionWindow(Base):
    __tablename__ = "ai_detection_windows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    detection_result_id = Column(
        String, ForeignKey("ai_detection_results.id"), index=True, nullable=False
    )
    window_index = Column(Integer, nullable=False)
    char_start = Column(Integer, nullable=False)
    char_end = Column(Integer, nullable=False)
    page_number = Column(Integer, default=1)
    binoculars_score = Column(Float, nullable=True)
    dna_score = Column(Float, nullable=True)
    risk_level = Column(String, default="LOW")  # "LOW", "ELEVATED", "HIGH"
    excerpt = Column(String, nullable=True)

    detection_result = relationship("AIDetectionResult", back_populates="windows")
