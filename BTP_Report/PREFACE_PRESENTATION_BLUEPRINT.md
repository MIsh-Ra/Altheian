# BTP Preface Presentation Blueprint (Canva-Ready Edition)

**Project Title:** Alethian v3.0: Dual-Engine Academic Plagiarism & Zero-Shot AI Forensics Platform  
**Target Duration:** 10 Minutes + 5 Minutes Q&A / Live Demonstration  
**Target Audience:** Faculty Review Committee, Project Evaluators, Department Deans, and External Examiners  
**Tooling Guide:** Specifically formatted for rapid, drag-and-drop authoring in **Canva** (using cards, badges, split screens, and high-contrast academic palettes).

---

## Canva Visual Style Guide & Theme Palette

When designing these slides in Canva, use this clean, modern academic theme:

- **Background:** Crisp Off-White / Light Gray (`#F8FAFC` or `#0F172A` if using Dark Mode).
- **Primary Text:** Deep Charcoal / Ink (`#1E293B`).
- **Brand Accent 1 (Primary / Trust):** Academic Navy / Indigo (`#1E40AF` or `#3B82F6`).
- **Brand Accent 2 (Success / Human):** Emerald Green (`#059669` or `#10B981`).
- **Brand Accent 3 (Warning / AI):** Amber / Orange (`#D97706` or `#F59E0B`).
- **Brand Accent 4 (Danger / Plagiarism):** Crimson Red (`#DC2626` or `#EF4444`).
- **Typography:**
  - **Headings:** Bold Sans-Serif (`Inter`, `Montserrat`, or `Poppins Bold`).
  - **Body / Descriptions:** Clean Neutral (`Inter Regular`, `Public Sans`, or `Open Sans`).
  - **Data / Code / Badges:** Monospace (`JetBrains Mono`, `Roboto Mono`, or `Space Mono`).
- **Canva Layout Elements:**
  - Rounded rectangular cards (corner radius: 12-16px, subtle drop shadow).
  - Split 50/50 comparison containers with colored borders.
  - Two-tone pill badges (`bg-emerald-500/10 text-emerald-600`) for verdicts and confidence scores.

---

## Slide 1: Title & Project Credentials (0:00 - 0:45)

### Canva Layout & Elements
- **Layout:** Centered Hero Title Card with clean top margin.
- **Visuals:**
  - Top Left: University Crest / LNMIIT Logo.
  - Top Right: Alethian Shield Monogram (`Shield with verified checkmark`).
- **Header:** **Alethian v3.0**
- **Sub-header:** A Dual-Engine Academic Integrity & Zero-Shot AI Forensics Platform
- **Footer Metadata Container:**
  - **Team Members:** [Your Name] (Roll No.) & [Partner Name] (Roll No.)
  - **Supervisor:** [Advisor Name], Department of Computer Science & Engineering
  - **Infrastructure Badge:** `NVIDIA DGX Cluster (Tesla V100 GPU 4)`

### Plain-English Evaluator Decoder
- **Alethian:** From the Greek *Aletheia* (unconcealed truth). An automated forensic platform designed to determine if academic research was genuinely written by students, copied from past theses/web, or synthesized by AI models.

### Speaker Script (What to Say)
> "Good morning, respected members of the evaluation committee, project supervisors, and deans. Today, we present Alethian Version 3.0. 
> Over the past two years, the emergence of frontier Generative AI has fundamentally disrupted university evaluation. Traditional plagiarism tools rely on finding identical word-for-word copies, rendering them completely ineffective against AI-generated prose. Alethian is our answer: an enterprise-grade, on-premise system that unifies deterministic plagiarism verification with mathematical, zero-training AI forensics."

---

## Slide 2: The Modern Academic Integrity Dilemma (0:45 - 1:45)

### Canva Layout & Elements
- **Layout:** 3 Horizontal Cards (Red, Amber, Purple theme).
- **Card 1 (Left - Crimson):** **Plagiarism 1.0 is Outdated**
  - Icon: File Copy / Strikethrough
  - Subtext: Students no longer copy-paste paragraphs from Wikipedia or past theses. They prompt LLMs (ChatGPT, Claude) to rewrite text, changing syntax while keeping core ideas.
- **Card 2 (Center - Amber):** **Commercial AI Checkers are Flawed**
  - Icon: Alert Triangle / Broken Shield
  - Subtext: Tools like GPTZero and Copyleaks use black-box classifiers that overfit. They falsely accuse non-native English (ESL) students over 20% of the time due to simple sentence patterns.
- **Card 3 (Right - Purple):** **Trivial Evasion Hacks**
  - Icon: Bug / Hidden Eye
  - Subtext: Students insert invisible zero-width spaces (`\u200B`), Cyrillic lookalike letters, or white text to completely blind standard document extractors.

### Plain-English Evaluator Decoder
- **ESL Bias:** Non-native English students who write in simple, formal English often get falsely accused of using AI because their sentences have low vocabulary variance.
- **Adversarial Tampering:** Intentional tricks (like hidden invisible letters) that make a document look normal to a human eye but trick computer checkers into seeing gibberish.

### Speaker Script (What to Say)
> "To understand why universities need a new approach, we must acknowledge that academic dishonesty has transformed. First, traditional tools look only for verbatim strings. When a student uses an LLM to rephrase a paper, traditional similarity shows 0%. 
> Second, the commercial AI detectors universities adopted are fundamentally unfair: studies prove they have high false positive rates against students writing in English as a second language because formulaic sentences mimic AI patterns.
> Third, students easily bypass detectors by inserting invisible zero-width characters between words. Alethian v3 was engineered to eliminate all three failure modes."

---

## Slide 3: Commercial Failure Case Study: Turnitin's Blind Spots (1:45 - 2:45)

### Canva Layout & Elements
- **Layout:** 2-Column Side-by-Side Comparison (Left: Turnitin Blackbox, Right: The Reality).
- **Left Container (Red Tinted):** **What Turnitin Does on a Real BTP Report**
  - `28% Total Similarity Reported` (Massively inflated).
  - `18% Plagiarism Penalty` on the mandatory university Certificate of Originality & Declaration!
  - `8% Penalty` on the student's own earlier semester draft.
  - `0% AI Detected` (Missed AI-generated literature review sections).
  - `Report Formatting Destroyed`: Converts the thesis into flat plain text, stripping all LaTeX equations, figures, and tables.
- **Right Container (Blue Tinted):** **The Academic Reality**
  - University declarations are mandatory templates; punishing students for them is mathematically absurd.
  - Students submitting their final thesis shouldn't be penalized for their own earlier progress reports.
  - Genuine AI-paraphrased sections go completely unnoticed while formulas and diagrams get deleted.

### Plain-English Evaluator Decoder
- **Boilerplate Text:** Fixed, standard legal wording mandated by the college (e.g., *'I hereby declare that this project report titled...'*). It is identical for all 500 students in a batch.

### Speaker Script (What to Say)
> "Here is a concrete case study comparing commercial software against reality on an actual 34-page LNMIIT BTP thesis. 
> When run through Turnitin, the report produced a 28% similarity score. But when we inspected the breakdown, 18% of that penalty came from the mandatory university Certificate of Originality and Candidate Declaration! Furthermore, it flagged 8% similarity against the student's own mid-term draft. 
> Worse, Turnitin reported 0% AI detection despite entire subsections of the literature review being generated by ChatGPT, and its exported report stripped all LaTeX formulas and figures into unreadable plain text. This is why an in-house forensic system is essential."

---

## Slide 4: The Alethian Architecture: Decoupled Dual-Engine (2:45 - 3:45)

### Canva Layout & Elements
- **Layout:** System Architecture Diagram (Canva Flowchart / 3 Columns).
- **Column 1 (Client):**
  - React 19 Frontend (Focus Canvas Reader + Forensic Inspector + Page Radar).
  - Live WebSocket telemetry updates.
- **Column 2 (FastAPI Gateway & Message Broker):**
  - FastAPI async API (Uvicorn).
  - PostgreSQL 15 (Relational Store) + Qdrant (Dense Vector DB) + Redis (Task Queue).
- **Column 3 (Decoupled Worker Split):**
  - **Celery CPU Worker (`celery_worker`):** Ingestion, 6-gram shingling, MinHash, live web crawling.
  - **Celery GPU Worker (`celery_ai_worker`):** Pinned exclusively to **GPU 4** on DGX cluster (`--pool=solo`), running zero-shot statistical models.

### Plain-English Evaluator Decoder
- **Decoupled Workers:** Separating the computer's tasks so that heavy AI calculations on the GPU run independently without slowing down file uploads, database queries, or PDF downloads.
- **Dense Vector Search:** Searching for concepts and meanings rather than just exact matching keywords.

### Speaker Script (What to Say)
> "This slide illustrates our end-to-end architecture. Alethian is cleanly partitioned into a decoupled dual-engine system. 
> On the left, our React 19 client connects to an asynchronous FastAPI gateway. When a thesis is uploaded, the document is dispatched into two parallel streams. 
> Our CPU Celery worker handles text parsing, shingling, and real-time scholarly web searches. Meanwhile, our GPU Forensics worker runs completely isolated on GPU 4 of our campus NVIDIA DGX cluster using a solo pool. This architectural separation prevents GPU memory deadlocks, guarantees zero blocking, and enables concurrent multi-user evaluations."

---

## Slide 5: Mathematical Innovation: Zero-Shot Binoculars (3:45 - 5:00)

### Canva Layout & Elements
- **Layout:** Split Card (Top: The Core Formula, Bottom: The ESL Invariant).
- **Formula Card (Navy Blue):**
  $$\text{Binoculars}(s) = \frac{\log \text{PPL}_{M_{\text{perf}}}(s)}{\log \text{xPPL}_{M_{\text{obs}}, M_{\text{perf}}}(s)}$$
  - Paired models from the `Qwen2.5-0.5B` family (Observer = Base, Performer = Instruct).
  - **No training data required.** Operates on intrinsic probability mode-seeking.
- **The ESL Self-Normalization Breakthrough (Green Card):**
  - **Human Student (ESL):** Uses simple words $\rightarrow \text{PPL}$ drops $\downarrow$, but cross-perplexity $\text{xPPL}$ also drops $\downarrow$.
  - **The Invariant:** $\frac{\downarrow \text{PPL}}{\downarrow \text{xPPL}} \approx 1.0 \implies \mathbf{T0\_HUMAN}$ (No False Accusations).
  - **AI Model:** Selects strictly high-probability modal tokens $\rightarrow \text{PPL}$ is unnaturally low relative to cross-perplexity $\implies \text{Ratio} \ge 1.07 \implies \mathbf{T3\_AI}$.

### Plain-English Evaluator Decoder
- **Perplexity (Surprise):** How surprised a language model is by the author's choice of words. High perplexity = creative, varied human writing. Low perplexity = predictable, formulaic text.
- **Binoculars Ratio:** Instead of judging a student on single words, Binoculars looks through "two lenses" (an observer and a performer). If a human writes simply, both lenses adjust equally, keeping the score fair.

### Speaker Script (What to Say)
> "Our core scientific innovation is zero-shot AI forensics using the Binoculars formulation. Rather than training a machine learning classifier that becomes obsolete whenever GPT-5 or Claude 4 releases, we measure the fundamental mathematical signature of all autoregressive models: mode-seeking.
> Modern LLMs pick words that minimize cross-entropy, creating a smooth, statistically predictable probability landscape. We pass text through two paired Qwen2.5 models. 
> Notice the critical mathematical breakthrough: Binoculars is a ratio. When a non-native English student writes with simple vocabulary, both the numerator and denominator decrease by the exact same proportion. The ratio stays near 1.0. This mathematically guarantees that honest students are never falsely penalized for writing simply."

---

## Slide 6: 3-Stage Cascaded Forensics & Paragraph Localization (5:00 - 6:00)

### Canva Layout & Elements
- **Layout:** 3 Step Funnel / Process Cards (Left to Right).
- **Stage 0 (Red Shield):** **Adversarial Gate & Normalization**
  - UTS #39 Unicode confusable normalization (detects Cyrillic lookalikes).
  - Invisible zero-width character stripping (`\u200B`, `\uFEFF`).
  - 150-Token Abstention Gate (refuses to guess on short snippets).
- **Stage 1 (Blue Funnel):** **Dual-Stream Inference (< 2.8 GB VRAM)**
  - Fast Binoculars + DNA-DetectLLM (paraphrase template stability).
  - Classifies 90% of documents in < 1.2s.
- **Stage 2 (Purple Arbitration):** **Consensus Escalation**
  - Escalates borderline cases (scores 1.01 to 1.07) to Meta-Llama-3 & DeBERTa-v3 cross-encoders.
- **Bottom Callout Banner (Green):**
  - **WCP+NOT Algorithm:** Segment-level paragraph localization. Pinpoints the exact paragraph and page where human prose ends and AI text begins.

### Plain-English Evaluator Decoder
- **Localization:** Telling the professor *exactly which paragraph* on *which page* is AI-written, rather than just giving a vague overall score like "30% AI".

### Speaker Script (What to Say)
> "In production, our AI forensics executes in three cascaded stages. 
> Stage 0 acts as our anti-cheat shield: it strips invisible zero-width spaces, normalizes homoglyphs, and enforces our 150-token minimum length threshold. 
> Stage 1 runs our dual-stream Qwen models in FP16 precision with Scaled Dot-Product Attention, completing inference in just 1.2 seconds with under 2.8 GB of VRAM. 
> If a document falls in the borderline zone, Stage 2 arbitrates using Llama-3 and DeBERTa cross-encoders. Crucially, our WCP+NOT algorithm performs paragraph boundary localization—showing the professor the exact sentence where human writing ends and AI generation starts."

---

## Slide 7: Citation-Aware Multi-Hop Web Dragnet v2.0 (6:00 - 6:45)

### Canva Layout & Elements
- **Layout:** 2-Column Split Card (Left: Search Sources, Right: Smart Citation Logic).
- **Left Box (Search Sources):**
  - Real-time deep crawl across: `Google`, `DuckDuckGo`, `Brave Search`, `arXiv`, `CrossRef`, `Semantic Scholar`, `Google Books`.
  - Captures unindexed preprints, tech blogs, and research papers not in local databases.
- **Right Box (Citation Intelligence):**
  - **In-Text Citation Parser:** Recognizes `[1]`, `[1-3]`, and `(Author, Year)` formats.
  - **Bibliography Decoupling:** Isolates References section automatically.
  - **Citation Exemption:** Verified citations are tagged in **Emerald Green Underline** and excluded from plagiarism penalty!

### Plain-English Evaluator Decoder
- **Citation Exemption:** If a student quotes a paper and includes '[1]' with proper reference, a standard checker flags it as stolen text. Alethian automatically recognizes the citation and excludes it from the plagiarism penalty.

### Speaker Script (What to Say)
> "Traditional plagiarism systems fail on modern web sources because they either check only static offline archives or flag properly referenced citations. 
> In Version 3, we built the Citation-Aware Web Dragnet. It performs concurrent multi-hop searches across DuckDuckGo, Brave, arXiv, Semantic Scholar, and CrossRef to find newly published papers and preprints. 
> More importantly, our citation parser reads in-text markers like bracketed numbers or author-year citations. When a passage is properly cited, Alethian underlines it in green and exempts it from the plagiarism penalty. We reward proper academic attribution instead of punishing it."

---

## Slide 8: In-Situ Vector PDF Annotation: 100% Visual Fidelity (6:45 - 7:30)

### Canva Layout & Elements
- **Layout:** Before / After Visual Card.
- **Top / Left (The Problem with Legacy Export):**
  - Shows plain-text corrupted view: Broken equations, lost diagrams, ruined tables.
- **Bottom / Right (The Alethian v3.0 Innovation):**
  - **100% Visual Fidelity:** Original student PDF is preserved in its exact vector layout.
  - **Non-Destructive Vector Highlights:** Red (verbatim), Orange (paraphrase), Green (citation), Graduated Blue (AI).
  - **Margin Sticky Badges:** Interactive notes detailing source URL, author, and match percentage.
  - **Executive Audit Certificate (Pages 1-3):** Dean's signature block, originality gauge, and forensic breakdown prepended directly to the thesis.

### Plain-English Evaluator Decoder
- **In-Situ Annotation:** Placing highlights directly onto the student's original PDF pages (on top of their actual figures and math formulas) without reformatting or damaging the document.

### Speaker Script (What to Say)
> "One of our most significant breakthroughs is our in-situ PDF annotation engine. Previous tools—and earlier iterations of our project—stripped PDFs to plaintext to add highlights, which destroyed mathematical formulas, tables, and diagrams. 
> In Alethian v3.0, we engineered a non-destructive vector overlay engine using PyMuPDF. We project color-coded highlights and margin badges directly onto the exact vector coordinates of the student's original PDF. 
> The student's LaTeX equations, circuit diagrams, and graphs remain 100% intact. We prepend a 3-page formal executive audit certificate, giving professors an official university sign-off sheet stitched directly with the student's annotated thesis."

---

## Slide 9: Scholarly UI: The Unslop Craft Standard (7:30 - 8:15)

### Canva Layout & Elements
- **Layout:** Screenshot Showcase with Feature Callout Badges.
- **Centerpiece:** High-resolution screenshot of the Alethian Focus Canvas & Inspector.
- **Callout 1 (Top Bar):** **Responsive Header & Export Toolbar**
  - `[Full Audit (PDF)]`, `[Summary Only]`, `[JSON]`, `[PRINT]` buttons with responsive wrap.
- **Callout 2 (Left Margin):** **Page Radar Strip**
  - Vertical thumbnail strip with color-coded risk bars for rapid navigation.
- **Callout 3 (Center):** **Focus Canvas**
  - High-legibility paper-white reading mode.
- **Callout 4 (Right):** **Plain-English Evaluator Tooltips `(i)`**
  - Hover-over explanations demystifying technical metrics for non-technical professors.

### Speaker Script (What to Say)
> "Here is our newly redesigned frontend, built with React 19 under our Unslop Craft Standard. We rejected cluttered dashboards and neon gimmicks in favor of a clinical, archival reading room aesthetic.
> The thesis occupies a spacious Focus Canvas with vector-accurate overlays. On the left, our Page Radar strip lets faculty scan through 40 pages in seconds and jump directly to highlighted sections. 
> Notice our top export toolbar: professors can download the complete bundle or a 3-page summary with one click. Every match and AI tier includes an interactive tooltip that explains the forensic evidence in plain English, ensuring non-technical faculty can evaluate reports with total confidence."

---

## Slide 10: Head-to-Head Comparative Study: Turnitin vs. Alethian (8:15 - 9:00)

### Canva Layout & Elements
- **Layout:** Large High-Contrast Comparison Table Card.

| Evaluation Criterion | Turnitin Commercial Output | Alethian v3.0 Production Output | Advantage |
|:---|:---:|:---:|:---:|
| **Reported Plagiarism** | **28% (Distorted)** | **11.6% (Clean Overlap)** | **Eliminates False Flags** |
| **Declaration / Certificate** | **Flagged as Plagiarized (18%)** | **Exempted (0% Penalty)** | **Protects College Forms** |
| **Student's Own Past Drafts** | **Flagged as Plagiarized (8%)** | **Isolated as "Author's Draft"** | **Prevents Self-Penalization** |
| **AI Writing Detection** | **0% AI Detected (Missed)** | **Localized (Page 17 @ 72.5%)** | **Detects Subtle LLM Text** |
| **Exported PDF Fidelity** | **Stripped to Raw Text** | **100% Visual Fidelity (Formulas & Figures intact)** | **Zero Formatting Loss** |
| **Data Sovereignty** | US Commercial Cloud | **On-Premise University DGX Cluster** | **Full Campus Data Privacy** |

### Speaker Script (What to Say)
> "This slide presents our head-to-head empirical comparison evaluated on an actual 34-page BTP report submitted at our university. 
> Turnitin reported an inflated 28% similarity score, with 18% caused entirely by the college's own certificate template and 8% from the student's prior draft. Turnitin detected zero percent AI writing and destroyed the document's equations upon export. 
> In contrast, Alethian reported an honest 11.6% similarity, recognized and exempted the certificate forms, isolated the author's previous draft, and pinpointed the AI-generated paragraph on Page 17 with 72.5% confidence—all while preserving 100% of the original equations and figures in our exported PDF. Furthermore, Alethian runs entirely on our campus DGX cluster, keeping university research strictly confidential."

---

## Slide 11: Hardware Profiling & Test Suite Rigor (9:00 - 9:45)

### Canva Layout & Elements
- **Layout:** 4 Metric Dashboard Cards (2x2 Grid).
- **Card 1 (Top Left - Navy):** **GPU Memory Footprint**
  - **2.78 GB Peak VRAM** on Tesla V100 (GPU 4).
  - Leaves **> 25 GB VRAM free** for other lab users.
- **Card 2 (Top Right - Emerald):** **Inference Throughput**
  - **1.24 Seconds** average latency for a 20-page thesis.
  - Sub-1.85s for a full 34-page BTP report.
- **Card 3 (Bottom Left - Blue):** **Automated Test Coverage**
  - **70 Pytest Backend Tests** (100% Pass Rate).
  - **23 Vitest Frontend Tests** (100% Pass Rate).
- **Card 4 (Bottom Right - Purple):** **Adversarial Accuracy**
  - **0.0% False Positive Rate** on authentic student holdouts.
  - **100% Capture Rate** on zero-width and homoglyph attacks.

### Speaker Script (What to Say)
> "From an AI systems engineering perspective, we prioritized efficiency and deterministic reliability. 
> By migrating our Stage 1 models to Qwen2.5-0.5B with FP32 logit upcasting, we slashed VRAM consumption from 28 GB down to just 2.8 GB. This allows Alethian to run comfortably on GPU 4 of our DGX cluster while leaving over 25 GB of memory free for other departmental researchers. 
> Our automated test suite includes 70 backend Pytest cases and 23 frontend Vitest cases, all passing with zero regressions. In empirical testing, we achieved a 0% false positive rate on legitimate student holdout theses."

---

## Slide 12: Conclusion & Transition to Live Demo (9:45 - 10:00)

### Canva Layout & Elements
- **Layout:** Centered Summary Card with 4 Key Takeaways + Live Demo Button.
- **Key Takeaways:**
  1. **Dual-Engine Precision:** Deterministic plagiarism search married with zero-training AI forensics.
  2. **Fair to Students:** Mathematical self-normalization prevents false accusations on ESL authors.
  3. **Turnitin Superiority:** In-situ vector PDF annotation, boilerplate exemption, and localized AI detection.
  4. **On-Premise Ready:** Deployed live on university DGX cluster with sub-2-second inference.
- **Call to Action Banner:** *"We now invite the committee to inspect the live platform on the campus server."*

### Speaker Script (What to Say)
> "To conclude: Alethian v3.0 provides an academically rigorous, mathematically proven, and computationally lightweight solution to the academic integrity challenge. It protects students from unfair false accusations, gives faculty actionable evidentiary reports with pristine visual fidelity, and runs autonomously on our university's own hardware.
> We thank the committee for your time, and we now welcome your questions and invite you to view the live demonstration."

---

## Quick Reference Cue Card (Time Allocation)
- **Slide 1 (0:00 - 0:45):** Title & Project Credentials
- **Slide 2 (0:45 - 1:45):** The Modern Academic Integrity Dilemma
- **Slide 3 (1:45 - 2:45):** Turnitin's Blind Spots (Case Study)
- **Slide 4 (2:45 - 3:45):** Decoupled Dual-Engine Architecture
- **Slide 5 (3:45 - 5:00):** Zero-Shot Binoculars & The ESL Invariant
- **Slide 6 (5:00 - 6:00):** 3-Stage Cascaded Forensics & Localization
- **Slide 7 (6:00 - 6:45):** Citation-Aware Web Dragnet v2.0
- **Slide 8 (6:45 - 7:30):** In-Situ Vector PDF Annotation
- **Slide 9 (7:30 - 8:15):** Scholarly UI & Evaluator Tooltips
- **Slide 10 (8:15 - 9:00):** Turnitin vs. Alethian Comparative Study
- **Slide 11 (9:00 - 9:45):** Hardware Efficiency & Test Rigor
- **Slide 12 (9:45 - 10:00):** Conclusion & Live Demo
