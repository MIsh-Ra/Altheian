# BTP Preface Presentation Blueprint

**Project Title:** Alethian v3.0: Dual-Engine Academic Plagiarism & Zero-Shot AI Forensics Platform  
**Target Duration:** 10 Minutes + 5 Minutes Q&A / Live Demonstration  
**Target Audience:** Faculty Review Committee, Project Evaluators, and Department Deans  

---

## Slide 1: Title & Credentials (0:00 - 0:45)

### Slide Layout & Visuals
- **Header:** Alethian v3.0: Dual-Engine Academic Plagiarism & AI Forensics Platform
- **Sub-header:** A Zero-Training Autoregressive Detection Architecture & Scholarly Forensic Workbench
- **Visual:** Clean university crest + Alethian system monogram.
- **Presenter Names:** [Your Name] & [Teammate Name]
- **Supervisor:** [Advisor Name], Department of Computer Science & Engineering

### Speaker Script (What to Say)
> "Good morning, respected members of the evaluation committee. Today, we are presenting Alethian Version 3.0. Over the past several semesters, generative AI has fundamentally shifted the nature of academic dishonesty. Where students once cut and pasted text from Wikipedia or seniors' theses, they now prompt frontier LLMs to synthesize thesis-grade prose that eludes traditional plagiarism checkers. Alethian is our answer: a dual-engine architecture that marries deterministic token retrieval with mathematical, zero-training AI forensics."

---

## Slide 2: The Academic Integrity Crisis (0:45 - 2:00)

### Slide Layout & Visuals
- **Three Core Vulnerabilities in Existing Tools:**
  1. **Traditional Plagiarism Checkers are Obsolete:** Tools like Turnitin and legacy shinglers only search for identical word sequences. Paraphrased or newly generated LLM text shows 0% similarity.
  2. **Supervised AI Detectors are Discriminatory & Fragile:** Classifiers like GPTZero or RoBERTa exhibit high False Positive Rates (> 20%) on non-native English (ESL) students and fail when new models release.
  3. **Trivial Adversarial Evasion:** Simple attacks like inserting invisible zero-width spaces (`\u200B`) or Cyrillic homoglyphs completely blind standard text extractors.

### Speaker Script (What to Say)
> "To understand why a new system was necessary, we must examine the failure modes of existing platforms. First, traditional plagiarism checkers are structurally blind to generative AI because synthetic prose is syntactically novel. Second, the commercial AI detectors that universities adopted rely on supervised classifiers that overfit to specific datasets. Studies demonstrate that these classifiers systematically flag non-native English students who write in simple, formulaic sentence structures. And third, students can bypass detection by simply injecting zero-width spaces or Cyrillic lookalikes. Alethian v3 was engineered from the ground up to solve all three issues."

---

## Slide 3: The Alethian Architecture: Decoupled Dual-Engine (2:00 - 3:15)

### Slide Layout & Visuals
- **Visual:** Embed [`figures/system_architecture.svg`](figures/system_architecture.svg)
- **Key Callouts:**
  - **FastAPI Gateway:** Async REST + WebSocket telemetry.
  - **Decoupled Celery Workers:** `celery_worker` (CPU I/O) vs. `celery_ai_worker` (GPU 4).
  - **Dual Datastores:** PostgreSQL 15 relational store + Qdrant high-dimensional vector index.

### Speaker Script (What to Say)
> "Here is our end-to-end system architecture. Alethian is partitioned into two asynchronous, decoupled execution pipelines. On the left, our plagiarism engine runs on CPU workers, extracting text, calculating 6-gram shingle Jaccard similarities, and querying a dense Qdrant vector database alongside a live Google Serper web dragnet. On the right, our GPU forensics worker runs in isolation on GPU 4 of our NVIDIA DGX cluster, preventing CUDA lockups and executing neural inference concurrently. Clients connect via a React 19 interface receiving real-time WebSocket progress broadcasts."

---

## Slide 4: Mathematical Innovation: Zero-Shot Binoculars (3:15 - 4:45)

### Slide Layout & Visuals
- **Visual:** Embed [`figures/dual_stream_binoculars.svg`](figures/dual_stream_binoculars.svg)
- **Mathematical Formula:**
  $$\text{Binoculars}(s) = \frac{\log \text{PPL}_{M_{\text{perf}}}(s)}{\log \text{xPPL}_{M_{\text{obs}}, M_{\text{perf}}}(s)}$$
- **The ESL Self-Normalization Invariant:**
  $$\text{ESL Student:} \quad \frac{\downarrow \text{PPL}_{\text{perf}}}{\downarrow \text{xPPL}_{\text{obs, perf}}} \approx 1.0 \implies \text{T0\_HUMAN (No False Accusation)}$$

### Speaker Script (What to Say)
> "Our core scientific contribution lies in our zero-training AI forensics. Rather than training a brittle classifier, we leverage the Binoculars paradigm published by Hans et al. in 2024. Autoregressive LLMs generate text by seeking probability modes, creating a smooth, low-entropy landscape. We pass the input text through a paired observer and performer model from the Qwen2.5 family.
> 
> Notice the critical mathematical breakthrough: Binoculars is a ratio. When an ESL student uses simple, predictable English connectors like 'furthermore' or 'in conclusion', both the performer perplexity in the numerator and the cross-perplexity in the denominator decrease in equal proportion. The ratio remains self-normalized near 1.0. This guarantees a near-zero false positive rate on legitimate student theses."

---

## Slide 5: The 3-Stage Cascaded Forensics Pipeline (4:45 - 6:00)

### Slide Layout & Visuals
- **Visual:** Embed [`figures/ai_forensics_pipeline.svg`](figures/ai_forensics_pipeline.svg)
- **Pipeline Breakdown:**
  - **Stage 0:** UTS #39 Confusables + Zero-Width Stripping + 150-Token Abstention Gate.
  - **Stage 1:** Dual-Stream Binoculars + DNA-DetectLLM (Paraphrase defense, +60ms CPU cost).
  - **Stage 2:** Borderline Consensus Arbitration (Meta-Llama-3 IRM + DeBERTa-v3 cross-encoder).
  - **Localization:** WCP+NOT Change-Point Algorithm.

### Speaker Script (What to Say)
> "In production, our AI forensics executes in three distinct stages. Before touching the GPU, Stage 0 sanitizes the text, normalizing homoglyphs, stripping invisible characters, and enforcing our 150-token abstention gate. Stage 1 executes our dual-stream Qwen2.5 models in FP16 with Scaled Dot-Product Attention, calculating both Binoculars and DNA-DetectLLM template stability.
> 
> If a score falls into the borderline indeterminate zone between 1.01 and 1.07, Stage 2 automatically escalates the document to an arbitration panel featuring Meta-Llama-3 and DeBERTa cross-encoders. Crucially, our WCP+NOT change-point algorithm segments the document into paragraphs, pinpointing the exact transition where human writing ends and AI text begins."

---

## Slide 6: Plagiarism & Report Engine Overhaul (6:00 - 7:00)

### Slide Layout & Visuals
- **Visual:** Embed [`figures/plagiarism_interval_merging.svg`](figures/plagiarism_interval_merging.svg)
- **Key Technical Highlights:**
  - **Substantive Token Filtering:** Ignores pure dot leaders (`. . . . . 12`) and Roman numerals.
  - **1D Mathematical Interval Merging:** Contiguous disjoint interval union eliminates shingle double-counting.
  - **Identical Twin Document Clamping:** Substantive coverage $> 85\% \implies 0.0\%$ originality.

### Speaker Script (What to Say)
> "In Version 3, we also completely overhauled the plagiarism calculation engine. Traditional systems inflate plagiarism scores by counting non-substantive formatting—like the dot leaders and page numbers in a Table of Contents. We engineered substantive token filtering that discards non-alphabetic formatting. Furthermore, we implemented 1D mathematical interval merging. When overlapping 6-grams match across consecutive sentences, we compute the union of disjoint character spans, ensuring no word is ever double-counted. For identical clone submissions, our 85% coverage clamp immediately drops originality to zero."

---

## Slide 7: Scholarly Forensic Interface (Unslop Standard) (7:00 - 8:00)

### Slide Layout & Visuals
- **Visual:** Embed [`figures/unslop_ui_flow.svg`](figures/unslop_ui_flow.svg) + Live Application Screenshot.
- **Design Innovations:**
  - **2-Pane Focus Canvas (75%-100%):** Paper-white thesis reading experience.
  - **Page Radar Margin Strip:** Proportional page strip with density color-coding.
  - **Collapsible Forensic Inspector:** 4 tabs (Matches, AI Audit, Sources, Sign-off).
  - **Plain-Language Evidentiary Labels:** Demystifies complex statistics.

### Speaker Script (What to Say)
> "Here is our newly redesigned frontend, built with React 19 under the Unslop Craft Standard. We eliminated cluttered four-column dashboards and neon UI gimmicks in favor of a quiet, archival reading room aesthetic. The student thesis occupies a full-page Focus Canvas with soft-tint highlights. On the left margin, a sleek Page Radar strip lets faculty jump directly to high-risk pages. On the right, a collapsible Forensic Inspector translates complex probability tensors into plain-language academic tiers: confirmed human, indeterminate, or high synthetic confidence, complete with an exportable digital signature seal."

---

## Slide 8: Empirical Validation on NVIDIA DGX Cluster (8:00 - 9:00)

### Slide Layout & Visuals
- **Data Table:** Benchmark comparison across the 5 Golden Documents:
  - `01_Human_Authentic`: 98.4% Originality, 0% AI (`T0_HUMAN`).
  - `02_Synthetic_AI`: 100.0% Originality, 99.2% AI (`T3_HIGH`).
  - `03_Hybrid_ChangePoint`: Exact inflection detected at Paragraph 3.
  - `04_Adversarial_Tampered`: 12 zero-width characters intercepted; flagged as AI.
  - `05_High_Overlap_Twin`: Clamped to 0.0% Originality (100% Plagiarized).
  - `1_Unindexed_Holdout_Theses`: Real LNMIIT theses evaluated with 0% False Positives.

### Speaker Script (What to Say)
> "All evaluation was conducted with zero mocking directly against real documents on our campus NVIDIA DGX cluster. Across our golden benchmark suite, authentic human research correctly achieved 0% AI signal and high originality. Pure GPT-4o documents were flagged with 99.2% synthetic confidence. In our hybrid sample, the system pinpointed the exact paragraph boundary where synthetic text was introduced. And in our adversarial test, twelve injected zero-width characters were trapped by Stage 0, normalized, and correctly evaluated. On real unindexed LNMIIT theses, we achieved a zero percent false positive rate."

---

## Slide 9: Hardware Efficiency & Engineering Rigor (9:00 - 9:45)

### Slide Layout & Visuals
- **Hardware Footprint:**
  - **GPU VRAM:** $< 2.8\text{ GB}$ on Tesla V100 (leaves $> 25\text{ GB}$ free).
  - **Inference Latency:** $1.24\text{ seconds}$ for a full 20-page thesis.
- **Testing Rigor:**
  - **70 Pytest Tests:** 100% Pass Rate on DGX backend.
  - **23 Vitest Tests:** 100% Pass Rate on React frontend.

### Speaker Script (What to Say)
> "From an AI systems engineering perspective, we prioritized deterministic bounds and efficiency. By migrating our Stage 1 observer/performer pair to Qwen2.5-0.5B with FP32 logit upcasting, we cut our GPU memory footprint from 28 GB down to just 2.8 GB. This leaves 25 GB of VRAM free on our V100 GPU for parallel jobs, achieving sub-1.3-second inference per document. Our test harness incorporates 70 unit and system tests in Python and 23 in Vitest, all passing with zero regressions."

---

## Slide 10: Conclusion & Transition to Live Demo (9:45 - 10:00)

### Slide Layout & Visuals
- **Summary Points:**
  - Zero-training statistical AI forensics without proprietary data.
  - Fair, self-normalizing protection for ESL and non-native student authors.
  - Localized paragraph-level change-point segmentation.
  - Production deployment on university cluster hardware.
- **Call to Action:** "We now invite the committee to view the live demonstration on the university DGX server."

### Speaker Script (What to Say)
> "To conclude: Alethian v3 provides an academically rigorous, mathematically proven, and computationally feasible solution to the generative AI crisis in universities. It protects non-native students from false accusations while providing deans and faculty with localized, forensic evidence. We now welcome your questions and invite you to inspect the live platform."

---

## Cue Card & Time Allocation Summary
- **Slide 1 (0:00-0:45):** Introduction & Project Premise
- **Slide 2 (0:45-2:00):** Academic Integrity Crisis & Flaws in Existing Tools
- **Slide 3 (2:00-3:15):** System Architecture & Decoupled Worker Design
- **Slide 4 (3:15-4:45):** Binoculars Math & The ESL Invariant
- **Slide 5 (4:45-6:00):** 3-Stage Cascaded Forensics & Localization
- **Slide 6 (6:00-7:00):** Plagiarism Engine Overhaul (Substantive Counting & Interval Merging)
- **Slide 7 (7:00-8:00):** Unslop UI & Focus Canvas
- **Slide 8 (8:00-9:00):** Empirical Results Table (DGX Cluster)
- **Slide 9 (9:00-9:45):** Hardware Profiling & Test Suite Rigor
- **Slide 10 (9:45-10:00):** Conclusion & Live Demo Transition
