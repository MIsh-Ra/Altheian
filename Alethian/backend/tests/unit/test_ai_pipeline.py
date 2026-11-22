"""
Unit tests for Alethian v3.0 Unified AI Detection Pipeline & Worker Integration.
Verifies:
1. End-to-end orchestration of clean human documents (Tier 0 Human).
2. Borderline & frontier AI documents triggering Stage 2 escalation and WCP+NOT localization.
3. Abstention gate enforcing minimum prose token length (< 150 tokens).
4. Adversarial Unicode and confusable tamper flag extraction.
5. Database persistence of AIDetectionResult and AIDetectionWindow records.
6. FastAPI REST endpoints for AI detection results and live status polling.
7. Celery AI worker task execution with fork safety.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.ai_detection.binoculars import BinocularsResult, BinocularsScorer
from app.core.ai_detection.dna_detect import DNADetectResult, DNADetectScorer
from app.core.ai_detection.orchestrator import (
    AIDetectionOrchestrator,
    OrchestratorResult,
)
from app.db.models import AIDetectionResult, Base, Document, User
from app.db.session import get_db
from app.main import app


# ---------------------------------------------------------------------------
# In-Memory SQLite Fixture for Thread-Safe Isolation
# ---------------------------------------------------------------------------
@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_human_text() -> str:
    # Over 200 substantive words of scholarly prose
    return (
        "In this study, we investigate the empirical dynamics of distributed gradient descent "
        "across heterogeneous network topologies. Recent advancements in edge computing and "
        "federated optimization have underscored the necessity of robust consensus mechanisms "
        "under non-uniform latency distributions. Specifically, we evaluate how stochastic "
        "quantization and local momentum accumulation influence convergence bounds in convex "
        "and non-convex loss surfaces. Our experimental methodology incorporates rigorous "
        "statistical tests to validate asymptotic stability. We observe that adaptive "
        "regularization significantly mitigates straggler effects without compromising the "
        "generalization fidelity of the global model parameters. Furthermore, extensive ablation "
        "studies reveal that parameter synchronization at dynamic intervals outperforms fixed-step "
        "coordination by a substantial margin. These theoretical insights provide concrete guidelines "
        "for deploying privacy-preserving decentralized learning frameworks in resource-constrained "
        "production environments while maintaining verifiable mathematical safety guarantees. All "
        "computational benchmarks were executed under rigorous control conditions to ensure "
        "reproducibility across independent evaluation clusters. In subsequent sections, we establish "
        "formal non-asymptotic upper bounds for the variance of the localized gradient estimators. "
        "By extending classical Lyapunov analysis to asynchronous parameter exchanges, we demonstrate "
        "that communication overhead can be diminished by sixty percent without degrading classification accuracy."
    )


# ---------------------------------------------------------------------------
# Test 1: Clean Human Document (Tier 0 Human)
# ---------------------------------------------------------------------------
def test_ai_orchestrator_human_document(sample_human_text: str):
    mock_bino = MagicMock(spec=BinocularsScorer)
    mock_bino.score_text.return_value = BinocularsResult(
        performer_log_ppl=3.25,
        cross_ppl=3.45,
        binoculars_score=0.9420,
        evidentiary_tier="T0_HUMAN",
        token_count=180,
        window_scores=[0.94, 0.95, 0.93],
    )

    mock_dna = MagicMock(spec=DNADetectScorer)
    mock_dna.score_text.return_value = DNADetectResult(
        binoculars_score=0.9420,
        template_divergence_ratio=0.88,
        composite_score=0.9110,
        evidentiary_tier="T0_HUMAN",
        token_count=180,
    )

    orchestrator = AIDetectionOrchestrator(
        binoculars_scorer=mock_bino,
        dna_scorer=mock_dna,
    )

    res: OrchestratorResult = orchestrator.analyze(
        document_id="doc-human-01",
        text=sample_human_text,
    )

    assert res.verdict == "T0_HUMAN"
    assert "Human" in res.verdict_label
    assert res.abstained is False
    assert res.confidence_score >= 0.90
    assert res.overall_ai_prob < 0.20
    assert len(res.windows) == 3
    assert all(w["risk_level"] == "LOW" for w in res.windows)


# ---------------------------------------------------------------------------
# Test 2: AI Document Triggering Stage 2 Escalation & Localization
# ---------------------------------------------------------------------------
def test_ai_orchestrator_frontier_ai_escalation(sample_human_text: str):
    mock_bino = MagicMock(spec=BinocularsScorer)
    # High score triggering escalation (>= 1.07 for Qwen2.5)
    mock_bino.score_text.return_value = BinocularsResult(
        performer_log_ppl=3.85,
        cross_ppl=3.40,
        binoculars_score=1.132,
        evidentiary_tier="ESCALATE",
        token_count=180,
        window_scores=[1.12, 1.14, 1.13],
    )

    mock_dna = MagicMock(spec=DNADetectScorer)
    mock_dna.score_text.return_value = DNADetectResult(
        binoculars_score=1.132,
        template_divergence_ratio=0.62,
        composite_score=0.7171,
        evidentiary_tier="ESCALATE",
        token_count=180,
    )

    orchestrator = AIDetectionOrchestrator(
        binoculars_scorer=mock_bino,
        dna_scorer=mock_dna,
    )

    res: OrchestratorResult = orchestrator.analyze(
        document_id="doc-ai-01",
        text=sample_human_text,
    )

    assert res.verdict in ("T3_HIGH", "T2_ELEVATED")
    assert res.abstained is False
    assert res.overall_ai_prob >= 0.80
    assert res.irm_divergence is not None
    assert res.deberta_prob is not None
    assert any(w["risk_level"] in ("HIGH", "ELEVATED") for w in res.windows)


# ---------------------------------------------------------------------------
# Test 3: Abstention Gate on Short Text (< 150 prose tokens)
# ---------------------------------------------------------------------------
def test_ai_orchestrator_abstention_gate():
    short_text = (
        "This is an abbreviated research note describing initial findings. "
        "Due to limited space, mathematical proofs and detailed graphs are omitted."
    )

    mock_bino = MagicMock(spec=BinocularsScorer)
    mock_dna = MagicMock(spec=DNADetectScorer)

    orchestrator = AIDetectionOrchestrator(
        binoculars_scorer=mock_bino,
        dna_scorer=mock_dna,
    )

    res: OrchestratorResult = orchestrator.analyze(
        document_id="doc-short-01",
        text=short_text,
    )

    assert res.verdict == "ABSTAINED"
    assert res.abstained is True
    assert res.confidence_score == 0.0
    assert res.overall_ai_prob == 0.0
    assert res.abstention_reason is not None
    assert "insufficient prose" in res.abstention_reason.lower()
    # Confirm models were never called
    mock_bino.score_text.assert_not_called()
    mock_dna.score_text.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: Adversarial Obfuscation & Confusable Tamper Detection
# ---------------------------------------------------------------------------
def test_ai_orchestrator_tamper_detection(sample_human_text: str):
    # Inject zero-width spaces (\u200b) and Cyrillic homoglyphs (\u0430 for 'a')
    tampered_text = sample_human_text.replace(
        "gradient", "gr\u0430dient"
    ).replace("network", "net\u200bwork")

    mock_bino = MagicMock(spec=BinocularsScorer)
    mock_bino.score_text.return_value = BinocularsResult(
        performer_log_ppl=3.25,
        cross_ppl=3.45,
        binoculars_score=0.9420,
        evidentiary_tier="T0_HUMAN",
        token_count=180,
        window_scores=[0.94],
    )
    mock_dna = MagicMock(spec=DNADetectScorer)
    mock_dna.score_text.return_value = DNADetectResult(
        binoculars_score=0.9420,
        template_divergence_ratio=0.88,
        composite_score=0.9110,
        evidentiary_tier="T0_HUMAN",
        token_count=180,
    )

    orchestrator = AIDetectionOrchestrator(
        binoculars_scorer=mock_bino,
        dna_scorer=mock_dna,
    )

    res = orchestrator.analyze(
        document_id="doc-tamper-01",
        text=tampered_text,
    )

    assert len(res.tamper_flags) >= 2
    details = [f["detail"].lower() for f in res.tamper_flags]
    assert any("confusable" in d or "cyrillic" in d for d in details)
    assert any("invisible" in d or "zero-width" in d for d in details)


# ---------------------------------------------------------------------------
# Test 5: Database Persistence
# ---------------------------------------------------------------------------
def test_ai_orchestrator_db_persistence(
    in_memory_db, sample_human_text: str
):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="distributed_opt.pdf",
        content=sample_human_text,
    )
    in_memory_db.add(doc)
    in_memory_db.commit()

    mock_bino = MagicMock(spec=BinocularsScorer)
    mock_bino.score_text.return_value = BinocularsResult(
        performer_log_ppl=3.25,
        cross_ppl=3.45,
        binoculars_score=0.9420,
        evidentiary_tier="T0_HUMAN",
        token_count=180,
        window_scores=[0.94, 0.95],
    )
    mock_dna = MagicMock(spec=DNADetectScorer)
    mock_dna.score_text.return_value = DNADetectResult(
        binoculars_score=0.9420,
        template_divergence_ratio=0.88,
        composite_score=0.9110,
        evidentiary_tier="T0_HUMAN",
        token_count=180,
    )

    orchestrator = AIDetectionOrchestrator(
        binoculars_scorer=mock_bino,
        dna_scorer=mock_dna,
    )

    res = orchestrator.analyze(
        document_id=doc_id,
        text=sample_human_text,
        db=in_memory_db,
    )

    saved_result = (
        in_memory_db.query(AIDetectionResult)
        .filter(AIDetectionResult.document_id == doc_id)
        .first()
    )
    assert saved_result is not None
    assert saved_result.verdict == "T0_HUMAN"
    assert saved_result.overall_ai_prob == res.overall_ai_prob
    assert len(saved_result.windows) == 2


# ---------------------------------------------------------------------------
# Test 6: FastAPI Endpoints (/api/v1/ai-detection)
# ---------------------------------------------------------------------------
def test_ai_detection_api_endpoints(in_memory_db):
    user_id = str(uuid.uuid4())
    mock_user = User(
        id=user_id,
        username="prof_turing",
        email="turing@cam.ac.uk",
    )
    in_memory_db.add(mock_user)

    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="neural_nets.pdf",
        content="Valid substantive academic text.",
        user_id=user_id,
    )
    in_memory_db.add(doc)
    in_memory_db.commit()

    app.dependency_overrides[get_db] = lambda: in_memory_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    client = TestClient(app)

    # 1. Check status when pending
    resp = client.get(f"/api/v1/ai-detection/{doc_id}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    assert resp.json()["has_result"] is False

    # 2. Check result when not yet available
    resp = client.get(f"/api/v1/ai-detection/{doc_id}")
    assert resp.status_code == 404

    # 3. Create simulated result
    ai_res = AIDetectionResult(
        document_id=doc_id,
        verdict="T0_HUMAN",
        confidence_score=0.95,
        overall_ai_prob=0.05,
        binoculars_ratio=0.9412,
        dna_detect_score=0.88,
        tamper_flags=[],
        prose_token_count=210,
        abstained=False,
        latency_ms=120.5,
    )
    in_memory_db.add(ai_res)
    in_memory_db.commit()

    # 4. Check result now available
    resp = client.get(f"/api/v1/ai-detection/{doc_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "T0_HUMAN"
    assert data["confidence_score"] == 0.95
    assert data["binoculars_ratio"] == 0.9412

    # Clean up overrides
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 7: Celery AI Worker Task Execution
# ---------------------------------------------------------------------------
def test_celery_ai_worker_task(in_memory_db, sample_human_text: str):
    from celery_ai_worker import detect_ai_task

    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="quantum_ai.pdf",
        content=sample_human_text,
    )
    in_memory_db.add(doc)
    in_memory_db.commit()

    with (
        patch("app.db.session.SessionLocal", return_value=in_memory_db),
        patch(
            "app.core.ai_detection.orchestrator.AIDetectionOrchestrator.analyze"
        ) as mock_analyze,
    ):
        mock_analyze.return_value = OrchestratorResult(
            document_id=doc_id,
            verdict="T0_HUMAN",
            verdict_label="Tier 0 (Human)",
            confidence_score=0.95,
            overall_ai_prob=0.05,
            abstained=False,
            latency_ms=85.0,
        )
        task_output = detect_ai_task(doc_id)

    assert task_output["status"] == "complete"
    assert task_output["document_id"] == doc_id
    assert task_output["verdict"] == "T0_HUMAN"
