# Alethian V2 — Academic Document Originality Platform

<p align="center">
  <strong>Enterprise-grade plagiarism detection for academic institutions</strong><br>
  Internal similarity analysis · Web dragnet scanning · Rich originality reports
</p>
---

## Overview

Alethian is a self-hosted, full-stack plagiarism detection platform built for universities and academic institutions. It analyzes submitted PDF documents against an internal archive of previously submitted work and the open web, producing detailed originality reports with match highlighting, source attribution, and faculty review workflows.

### Key Capabilities

| Feature | Description |
|:--------|:------------|
| **Internal Similarity** | Detects exact and paraphrased matches against your institutional document archive using MinHash + semantic embeddings (SentenceTransformer) stored in Qdrant |
| **Web Dragnet** | Searches suspicious text chunks via Serper/Google API with DuckDuckGo fallback, then semantically compares fetched web content |
| **Rich Reports** | Originality scores, page-level heatmaps, match cards with word-level diff (LCS), source breakdown charts, and PDF export |
| **Faculty Workflow** | Match exclusion with reasons, inline commenting, review verdicts, digital signatures |
| **Admin Panel** | Adjustable similarity thresholds, API status monitoring, archive statistics |
| **Real-time Updates** | WebSocket-based progress streaming from Celery worker via Redis pub/sub |

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Frontend   │────▶│   FastAPI    │────▶│ Celery Worker │
│   (React)    │◀────│   Backend    │◀────│   (Python)    │
└─────────────┘     └──────┬───────┘     └───────┬───────┘
      ▲ WebSocket          │                     │
      │ (Redis pub/sub)    │                     │
      └────────────────────┼─────────────────────┘
                           │
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
        ┌──────────┐ ┌──────────┐    ┌──────────┐
        │ Postgres │ │  Qdrant  │    │  Grobid  │
        │ (Users,  │ │ (Vector  │    │  (PDF    │
        │  Reports)│ │  Search) │    │  Parser) │
        └──────────┘ └──────────┘    └──────────┘
              ▲
              │
        ┌──────────┐
        │  Redis   │
        │ (Queue + │
        │  PubSub) │
        └──────────┘
```

---

## Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (v2+)
- **Python** 3.10+
- **Node.js** 18+ & npm
- ~2GB disk for ML models (downloaded on first run)

### 1. Clone & Configure

```bash
git clone <repository-url>
cd Alethian

# Copy and edit environment variables
cp .env.example .env
# Edit .env — set your SERPER_API_KEY and JWT_SECRET at minimum
```

### 2. Start Infrastructure

```bash
cd infrastructure
docker compose up -d
cd ..
```

This spins up PostgreSQL (port 5433), Redis (6379), Qdrant (6333), and Grobid (8070).

### 3. Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the API server
PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In a separate terminal — start the Celery worker
PYTHONPATH=. celery -A celery_worker worker --loglevel=info
```

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 5. Login

Navigate to `http://localhost:5173`. Default auto-registration is enabled — enter any email/password to create an account. For admin access, use the credentials set in `.env`.

---

## Project Structure

```
Alethian/
├── .env.example                 # Environment template
├── .env                         # Local config (gitignored)
├── run_full_tests.sh            # Zero-mock test runner
│
├── infrastructure/
│   └── docker-compose.yml       # Postgres, Redis, Qdrant, Grobid
│
├── backend/
│   ├── requirements.txt
│   ├── celery_worker.py         # Document processing pipeline
│   ├── app/
│   │   ├── main.py              # FastAPI app + router setup
│   │   ├── api/
│   │   │   ├── auth.py          # Login + JWT issuance
│   │   │   ├── documents.py     # Upload, list, WebSocket status
│   │   │   ├── reports.py       # Report CRUD, export, review
│   │   │   ├── admin.py         # Config management
│   │   │   └── dependencies.py  # Auth guards (get_current_user, require_admin)
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic settings from .env
│   │   │   ├── ingestion.py     # GrobidClient PDF parsing
│   │   │   ├── shingling.py     # Sliding windows + SentenceTransformer embeddings
│   │   │   ├── similarity.py    # Qdrant-based exact + semantic search
│   │   │   ├── web_dragnet.py   # Serper/DDG web search + content comparison
│   │   │   ├── content_fetcher.py  # URL scraping + snippet comparison
│   │   │   └── report_engine.py # Score calculation, heatmap, stats
│   │   ├── db/
│   │   │   ├── models.py        # SQLAlchemy ORM (User, Document, Report, Match, Source, HeatmapPage)
│   │   │   └── session.py       # Database engine + session factory
│   │   └── schemas/             # Pydantic request/response models
│   └── tests/
├── backend/                     # FastAPI backend & Celery workers (Plagiarism + AI Forensics)
│   ├── app/
│   │   ├── api/                 # REST endpoints (auth, documents, reports, ai-detection, admin)
│   │   ├── core/                # Core engines (shingling, similarity, web dragnet, AI forensics)
│   │   └── db/                  # SQLAlchemy models and sessions
│   ├── celery_worker.py         # Asynchronous plagiarism pipeline worker
│   ├── celery_ai_worker.py      # Dedicated GPU-accelerated AI forensics worker
│   └── tests/                   # Pytest test suite (unit and system tests)
│
├── frontend/                    # React 19 SPA (Unslop craft standard)
│   ├── src/
│   │   ├── pages/               # Login, Dashboard, ReportView
│   │   ├── components/report/   # ProseViewer, AIDetectionView, MatchCard, SourcePanel, etc.
│   │   ├── stores/              # Zustand state management
│   │   └── tests/               # Vitest test suite
│   └── package.json
│
├── docs/                        # Consolidated documentation & v3 specifications
│   ├── specs/                   # System architecture blueprints & data contracts
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT.md
│   ├── TESTING.md
│   └── UI_MODERNIZATION_ROADMAP.md
│
├── test_documents/              # Canonical empirical test suite & synthesizer
├── scripts/                     # Production ingestion and archive utilities
├── infrastructure/              # Docker Compose definitions (Postgres, Redis, Qdrant, Grobid)
├── backup/                      # Preserved legacy prototypes & v1/v2 archives
└── Local-Crawler/               # Institutional repository crawling tools
```

---

## Documentation Index

| Document | Path | Description |
|:---------|:-----|:------------|
| **This README** | `README.md` | Project overview and quick start |
| **BTP Handover & System Report** | `docs/V3_BTP_HANDOVER_AND_TECHNICAL_REPORT.md` | Master technical briefing for BTP report & presentation |
| **Documentation Hub** | `docs/README.md` | Complete index of all guides and specifications |
| **Backend Guide** | `backend/README.md` | API reference, worker pipeline, configuration |
| **Testing Guide** | `docs/TESTING.md` | Zero-mock test architecture, running tests |
| **Deployment Guide** | `docs/DEPLOYMENT.md` | Production deployment with Docker, Nginx, systemd |
| **API Specification** | `docs/specs/API_Spec_v2.md` | Full REST API reference |
| **SRS** | `docs/specs/Alethian_SRS_v2.md` | Software Requirements Specification |
| **Architecture Comparison** | `docs/specs/Architecture_Comparison_v3.md` | Dual-engine architecture design & trade-offs |

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| Frontend | React 19, Vite, TailwindCSS, Zustand, Recharts, Lucide |
| Backend | FastAPI, SQLAlchemy, Celery, Pydantic |
| ML/NLP | SentenceTransformer (all-MiniLM-L6-v2), Qdrant vector DB |
| PDF Parsing | Grobid (TEI-XML extraction) |
| Web Search | Serper (Google), DuckDuckGo (fallback) |
| Database | PostgreSQL 15, Redis 7 |
| Testing | pytest (backend), Vitest + RTL (frontend) |
| Infrastructure | Docker Compose |

---

## License

This project is developed for academic research purposes at Manipal University Jaipur. See the institution's academic integrity policy for usage guidelines.
