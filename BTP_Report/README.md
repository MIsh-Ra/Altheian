# Alethian v3.0: BTP Report & Presentation Workspace

Welcome! This directory contains the complete technical briefing, empirical data, vector graphics, and presentation blueprints for the **B.Tech Project (BTP) Final Report** and **Preface Presentation**.

---

## Directory Contents

```
BTP_Report/
├── README.md                           # This quick start guide
├── TECHNICAL_REPORT.md                 # Complete, comprehensive academic systems report
├── PREFACE_PRESENTATION_BLUEPRINT.md   # 12-slide Canva-ready presentation blueprint with speaker scripts
├── VIVA_DEFENSE_QA.md                  # Comprehensive defense Q&A master reference (5 technical domains)
│
├── figures/                            # Exported Vector SVGs & LaTeX snippets
│   ├── system_architecture.svg         # Complete decoupled dual-engine architecture
│   ├── ai_forensics_pipeline.svg       # 3-Stage cascaded AI detection & localization flow
│   ├── dual_stream_binoculars.svg      # Binoculars perplexity cross-ratio & ESL invariant
│   ├── localization_wcp_changepoint.svg# WCP+NOT paragraph boundary risk detection
│   ├── plagiarism_interval_merging.svg # Substantive word filtering & 1D interval merging
│   ├── unslop_ui_flow.svg              # 2-Pane Focus Canvas & Forensic Inspector layout
│   └── latex_figures.tex               # Drop-in LaTeX \includesvg / \includegraphics snippets
│
└── benchmarks/                         # Empirical test results & profiling
    ├── empirical_benchmark_results.md  # Detailed benchmark write-up with Turnitin comparison
    └── benchmark_metrics.csv           # Raw benchmark metrics across all test documents & real BTPs
```

---

## How to Use These Assets

### 1. Preparing the Final Presentation (Canva-Ready)
- Open [`PREFACE_PRESENTATION_BLUEPRINT.md`](PREFACE_PRESENTATION_BLUEPRINT.md) — it provides a complete **12-slide layout specifically designed for Canva**:
  - Color palette codes (`#1E293B`, `#1E40AF`, `#059669`, `#DC2626`).
  - Canva container instructions (cards, badges, 2-column split screens, comparison tables).
  - Word-for-word speaker scripts and time allocation cue cards (10 minutes total).
  - Dedicated slides on **Turnitin vs. Alethian Head-to-Head Comparison**, **In-Situ Vector PDF Annotation**, and **Citation-Aware Web Dragnet**.
  - All diagrams in [`figures/`](figures/) are scalable SVGs that drag and drop directly into Canva without any resolution loss.

### 2. Writing the BTP Final Report
- Open [`TECHNICAL_REPORT.md`](TECHNICAL_REPORT.md) — structured according to university BTP chapter formatting:
  - **Section 1.1:** **Faculty & Evaluator's Plain-English Decoder** (Translates every engineering term into simple academic terms so professors and evaluators are never confused).
  - **Chapter 1:** Introduction, Crisis in University Evaluation, & Objectives
  - **Chapter 2:** Literature Review & Mathematical Foundations (Binoculars formulation & ESL self-normalizing proof)
  - **Chapter 3:** System Architecture & Decoupled Worker Isolation (CPU vs. GPU 4 on DGX)
  - **Chapter 4:** Implementation Details (Stage 0-2 AI Forensics, Citation-Aware Web Dragnet v2.0, In-Situ Vector PDF Annotation Engine)
  - **Chapter 5:** Experimental Evaluation & Turnitin Head-to-Head Benchmarks on real LNMIIT BTP theses
  - **Chapter 6:** Conclusion & Future Scope

### 3. Preparing for Viva Voce / Faculty Cross-Examination
- Open [`VIVA_DEFENSE_QA.md`](VIVA_DEFENSE_QA.md) — covers 17 anticipated defense questions across 5 technical domains:
  - **Domain 1:** AI Detection & Autoregressive Mode-Seeking Mechanics.
  - **Domain 2:** Systems Engineering, Celery Decoupled Architecture, & DGX GPU Isolation.
  - **Domain 3:** Plagiarism Engine, Substantive Token Counting, & 1D Interval Merging.
  - **Domain 4:** Adversarial Evasion Defense (Zero-width character stripping, UTS #39 homoglyph normalization).
  - **Domain 5:** Turnitin Comparison, Citation Exemption, & In-Situ Vector PDF Preservation.

---

## Key Numbers & Concrete Results to Showcase

| Metric / Result | Value | Evaluator Significance |
|:---|:---:|:---|
| **Turnitin vs. Alethian (Real BTP Thesis)** | **28% vs. 11.6%** | Eliminates 18% false penalty on mandatory college declarations. |
| **Visual Document Fidelity** | **100% Vector Retention** | Preserved all 14 embedded figures & 509 formula/diagram paths in-situ. |
| **GPU 4 VRAM Footprint** | **2.78 GB** | Leaves $> 25\text{ GB}$ free on DGX Tesla V100 for other lab researchers. |
| **Inference Latency** | **1.24s (20 pages) / 1.84s (34 pages)** | Sub-2-second turnaround for full student dissertations. |
| **False Positive Rate (ESL / Authentic)** | **0.0%** | Proven fair on non-native English holdout engineering theses. |
| **Adversarial Capture Rate** | **100%** | 12/12 zero-width characters trapped by Stage 0 filter. |
| **Automated Test Suite Pass Rate** | **100%** | 70/70 backend Pytest + 23/23 frontend Vitest test cases passing. |
