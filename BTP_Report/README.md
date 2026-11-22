# Alethian v3.0: BTP Report & Presentation Workspace

Welcome! This directory contains the complete technical briefing, empirical data, vector graphics, and presentation blueprints for the **B.Tech Project (BTP) Final Report** and **Preface Presentation**.

---

## Directory Contents

```
BTP_Report/
├── README.md                           # This quick start guide
├── TECHNICAL_REPORT.md                 # Complete, comprehensive academic systems report
├── PREFACE_PRESENTATION_BLUEPRINT.md   # 10-slide presentation blueprint with speaker scripts & cue cards
├── VIVA_DEFENSE_QA.md                  # Comprehensive defense Q&A master reference
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
    ├── empirical_benchmark_results.md  # Detailed benchmark write-up with confusion matrix
    └── benchmark_metrics.csv           # Raw benchmark metrics across all test documents
```

---

## How to Use These Assets

### 1. Writing the BTP Final Report
- Open [`TECHNICAL_REPORT.md`](TECHNICAL_REPORT.md) — it is structured according to standard BTP chapter formatting:
  - **Chapter 1:** Introduction & Motivation
  - **Chapter 2:** Literature Review & Mathematical Formulations
  - **Chapter 3:** System Architecture & Decoupled Workers
  - **Chapter 4:** Implementation Details (Stage 0-2 AI Forensics, Plagiarism Interval Merging, Unslop UI)
  - **Chapter 5:** Experimental Evaluation & DGX Cluster Benchmarks
  - **Chapter 6:** Conclusion & Future Scope
- To insert figures into LaTeX, copy the code blocks from [`figures/latex_figures.tex`](figures/latex_figures.tex). All 6 diagrams are rendered as scalable, high-resolution vector SVGs in [`figures/`](figures/).

### 2. Preparing the Preface Presentation Slides
- Open [`PREFACE_PRESENTATION_BLUEPRINT.md`](PREFACE_PRESENTATION_BLUEPRINT.md) — it provides a complete 10-slide guide:
  - Exact slide layout and key bullet points.
  - Which SVG diagram to drag and drop into each slide.
  - Verbatim speaker scripts (what to say word-for-word).
  - Time allocation cue cards (total presentation duration: 10 minutes).
- SVGs can be dropped directly into PowerPoint, Google Slides, Keynote, or Marp presentations without any resolution loss.

### 3. Preparing for Viva Voce / Faculty Questions
- Open [`VIVA_DEFENSE_QA.md`](VIVA_DEFENSE_QA.md) — covers 11 anticipated technical questions across:
  - AI Detection & Autoregressive mode-seeking mechanics.
  - Mathematical proof of the ESL self-normalizing invariant.
  - Concurrency & Celery worker isolation on NVIDIA DGX cluster (GPU 4).
  - Plagiarism substantive token filtering & 1D interval merging.
  - Adversarial Unicode defense against zero-width spaces and homoglyphs.

---

## Key System Numbers to Remember
- **GPU 4 VRAM Footprint:** $\sim 2.8\text{ GB}$ (leaving $> 25\text{ GB}$ free on DGX Tesla V100/A100).
- **Inference Latency:** $\sim 1.24\text{ seconds}$ per 20-page dissertation.
- **AI Detection Thresholds:**
  - Ratio $< 1.01 \implies$ `T0_HUMAN` (Verified authentic human).
  - $1.01 \le \text{Ratio} < 1.07 \implies$ `T1_INDETERMINATE` (Stage 2 escalation).
  - Ratio $\ge 1.07 \implies$ `T3_HIGH` (High synthetic AI confidence).
- **Plagiarism Clamping:** Substantive coverage $> 85\% \implies 0.0\%$ originality (100% plagiarized).
- **Test Pass Rate:** 100% (70 backend Pytest + 23 frontend Vitest tests).
