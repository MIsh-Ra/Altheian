# Alethian v3.0: Comprehensive Testing & Evaluation Plan
## Eval-Driven Development (EDD) & Multi-GPU Verification Protocol

**Author:** AI Systems Engineering Board  
**Target:** Alethian v3.0 Backend Engine (Plagiarism Remediation + Zero-Training AI Forensics)  
**Date:** 2026-11-22  
**Status:** Mandatory Quality Gate — Pre-Implementation  

---

## 1. Executive Summary & Testing Philosophy

In accordance with our core engineering standard (**Eval-Driven Development**), **no engine heuristic or model pipeline will be implemented without an existing, failing test case and an automated evaluation assertion.**

AI text detection systems are uniquely prone to silent failures:
- **Numerical Instability:** FP16 overflow in 65k–128k vocabularies produces silent `NaN` or `Inf` scores.
- **Demographic Bias:** Non-native English (ESL) text suffers from low-perplexity false accusations.
- **Length Distortion:** Short spans (<150 tokens) spike False Positive Rates to 29%.
- **Surface Artifacts:** PDF line-breaks artificially separate human and AI text at $R^2 = 0.61$.
- **Adversarial Laundering:** Homoglyphs and zero-width characters evade naïve tokenizers.

To prevent these failure modes, Alethian v3.0 establishes a **4-Level Test Pyramid** backed by a curated **Golden Benchmark Suite**.

---

## 2. The 4-Level Testing Pyramid

```
                       ┌─────────────────────────┐
                       │        LEVEL 4:         │
                       │   End-to-End Cluster    │
                       │  Throughput & Concurrency│
                       │   (Celery Solo on V100s) │
                       └────────────┬────────────┘
                                    │
                       ┌────────────┴────────────┐
                       │        LEVEL 3:         │
                       │   Golden Benchmark Eval │
                       │ (7 Archetypes: ESL, AI, │
                       │   Twins, Hybrid, Tamper)│
                       └────────────┬────────────┘
                                    │
                       ┌────────────┴────────────┐
                       │        LEVEL 2:         │
                       │   GPU Kernel & Numerical│
                       │   Stability (FP16/FP32, │
                       │    SDPA, Zero-NaN Gate) │
                       └────────────┬────────────┘
                                    │
                       ┌────────────┴────────────┐
                       │        LEVEL 1:         │
                       │   Deterministic Unit    │
                       │  (Regex, UTS #39, Math, │
                       │   Tokenizers, Chunker)  │
                       └─────────────────────────┘
```

---

## 3. Level 1: Deterministic Unit Test Suite (CPU / Local)

These tests run in under 5 seconds on CPU with zero GPU dependencies, executing as pre-commit hooks.

### 1.1 Remediation Unit Tests (`test_remediation.py`)
- **`test_substantive_word_count_ignores_dots`**:
  Asserts that `". . . . . 12"` yields 0 substantive words while `"Chapter 1 Introduction"` yields 3.
- **`test_twin_document_coverage_clamp`**:
  A mock document with 90% merged substantive match coverage against the archive must clamp strictly to **0.0% Originality (100% Plagiarism)**.
- **`test_heatmap_density_merged_intervals`**:
  A 500-word page with 5 overlapping 30-word matches spanning the *same* 35 words must compute `density = 35 / 500 = 0.07`, NOT `150 / 500 = 0.30`.
- **`test_admin_key_persistence_redis`**:
  Verifies that sending a PATCH to `/admin/config` with `serper_api_key` stores and retrieves the value from Redis.

### 1.2 Stage 0 Preprocessor Unit Tests (`test_preprocessor.py`)
- **`test_uts39_confusable_normalization`**:
  Cyrillic homoglyphs (`'а'` U+0430, `'е'` U+0435, `'о'` U+043E) are normalized to ASCII `'a'`, `'e'`, `'o'`.
- **`test_invisible_unicode_stripping`**:
  Zero-width spaces (`U+200B`, `U+200C`, `U+200D`, `U+FEFF`) are stripped from prose text.
- **`test_tamper_alert_trigger`**:
  A text containing $\le 3$ anomalies yields `tamper_alert=False`. A text with $\ge 4$ anomalies yields `tamper_alert=True` with exact character offsets recorded.
- **`test_latex_and_equation_masking`**:
  `\begin{equation} E=mc^2 \end{equation}` and `$f(x) = \int_0^1 x dx$` are replaced with `[MATH]` and masked out of token scoring.
- **`test_parenthetical_citation_masking`**:
  `"(Vaswani et al., 2017)"` and `"[1, 4-7]"` are replaced with `[CIT]`.
- **`test_pdf_line_wrap_normalization`**:
  `"distri-\nbuted sys-\ntems"` is rejoined to `"distributed systems"`.
- **`test_abstention_floor_under_150_tokens`**:
  A 120-token paragraph emits `status="ABSTAIN"` and `reason="Insufficient prose length (120 < 150)"`.

---

## 4. Level 2: GPU Kernel & Numerical Stability Suite (DGX V100)

Executed on the DGX cluster to verify low-level CUDA, Tensor Core, and memory bounds.

### 2.1 FP16 / FP32 Logit Upcast Gate (`test_gpu_numerics.py`)
- **Assertion:** Softmax and Cross-Entropy over vocabulary sizes of $65,024$ (Falcon) and $128,256$ (Llama-3) must be computed in `float32`.
- **Failure Condition:** Any `NaN`, `-inf`, or `+inf` in the resulting log-perplexity tensor fails the build immediately.
- **Test Vector:** Feed synthetic adversarial logits with extreme dynamic range (`[-1000.0, +65500.0]`) to ensure no numerical overflow.

### 2.2 SDPA Kernel Dispatch Verification (`test_gpu_sdpa.py`)
- **Assertion:** On Volta `sm_70`, calling causal models with `attn_implementation="sdpa"` must successfully dispatch to PyTorch 2.6's xFormers-based `mem_efficient` kernel.
- **Failure Condition:** Fallback to un-fused Python loop attention or attempting to invoke `flash-attn` (which fails on sm_70).

### 2.3 VRAM Ceiling Verification (`test_gpu_vram_bounds.py`)
- **Test:** Run micro-batches of $B=4, L=512$ under `torch.inference_mode()`.
- **Bounds:**
  - GPU 1 (Falcon-7B Base): Peak VRAM must remain $\le 16.5 \text{ GiB}$ (well below 30.8 GiB usable limit).
  - GPU 3 (Falcon-7B Instruct): Peak VRAM must remain $\le 16.5 \text{ GiB}$.
  - GPU 6 (Llama-3-8B Base): Peak VRAM must remain $\le 19.5 \text{ GiB}$.
  - GPU 7 (Llama-3-8B Instruct + DeBERTa): Peak VRAM must remain $\le 23.5 \text{ GiB}$.

---

## 5. Level 3: Golden Benchmark Evaluation Suite

We define a curated evaluation dataset consisting of **7 distinct document archetypes** with ground-truth labels and strict metric assertions:

```
Alethian/backend/tests/golden_benchmarks/
├── TC1_archive_twin_15UCS032.pdf         # Ground Truth: 100% Plagiarism, Human AI Tier
├── TC2_clean_holdout_1125_UEC006.pdf     # Ground Truth: <15% Plagiarism, Human AI Tier
├── TC3_non_native_esl_academic.pdf       # Ground Truth: Clean Human (Fairness Benchmark)
├── TC4_gpt4o_pure_academic_thesis.pdf     # Ground Truth: Elevated AI (Tier 3)
├── TC5_hybrid_human_ai_manuscript.pdf    # Ground Truth: Mixed AI (Tier 2), Known Boundary
├── TC6_obfuscated_homoglyph_paper.pdf    # Ground Truth: Tamper Alert = True
└── TC7_short_abstract_excerpt.pdf        # Ground Truth: Abstain Floor (<150 tokens)
```

### Detailed Golden Assertions Matrix

| ID | Test Archetype | Input Artifact | Ground Truth Plagiarism | Ground Truth AI Tier | Pass/Fail Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-1** | **Archive Twin** | `15UCS032-19.pdf` | **$\ge 99.8\%$** | **Tier 0 (Human)** | Plagiarism $\ge 99.8\%$; AI score $B(s) \ge 0.9015$ (No false AI alert on historical archive) |
| **TC-2** | **Clean Holdout** | `1125__2884_...pdf` | $\le 15.0\%$ | **Tier 0 (Human)** | Plagiarism $\le 15\%$; AI score $B(s) \ge 0.9015$ |
| **TC-3** | **ESL Manuscript** | Pre-2022 Non-native Thesis | $\le 15.0\%$ | **Tier 0 (Human)** | **Strict Fairness:** $B(s) \ge 0.8536$ nominal cut (0 false positives on non-native writing) |
| **TC-4** | **Frontier AI Text** | GPT-4o Academic Paper | $\le 10.0\%$ | **Tier 3 (Elevated AI)** | $B(s) < 0.8350$; DNA score $< 0.75$; Stage 2 Llama corroborates |
| **TC-5** | **Hybrid Paper** | AI Section 1 + Human Body | Variable | **Tier 2 (Mixed AI)** | WCP+NOT detects boundary within $\pm 15$ tokens of actual injection |
| **TC-6** | **Adversarial Tamper** | Cyrillic 'а', 'е' substitutions | Normalized | **Tamper Alert** | `tamper_alert = True`, `tamper_count > 10`, text normalized before scoring |
| **TC-7** | **Short Excerpt** | 80-token abstract | N/A | **Abstain** | `abstained = True`, verdict suppressed |

---

## 6. Level 4: Regression, Concurrency & Celery Pipeline Testing

### 4.1 Celery Multi-GPU Concurrency Test (`test_celery_multigpu.py`)
- **Test:** Dispatch 10 concurrent analysis tasks to Redis.
- **Assertion:**
  - Tasks consume from `plagiarism_scan` (GPU 4) and `ai_detection` (GPUs 1 & 3) without CUDA initialization deadlocks.
  - No `RuntimeError: Cannot re-initialize CUDA in forked subprocess` occurs (validating `--pool=solo`).
  - Worker memory remains flat over 10 consecutive executions (zero CUDA memory leaks).

### 4.2 End-to-End API Integration Test (`test_e2e_unified_report.py`)
- **Flow:**
  1. Authenticate as faculty via `POST /api/v1/auth/login`.
  2. Upload `TC-5` (Hybrid paper) via `POST /api/v1/documents/upload`.
  3. Listen to Redis WebSocket status: `ingesting` $\rightarrow$ `indexing` $\rightarrow$ `internal_similarity` $\rightarrow$ `ai_primary_scan` $\rightarrow$ `complete`.
  4. Fetch `GET /api/v1/reports/{id}`:
     - Verify response contains both `plagiarism` object and `ai_detection` object.
     - Verify `ai_detection.windows` contains character-offset heatmap segments.
     - Verify `unified_verdict` presents due-process review guidelines.

---

## 7. Execution Protocol & Quality Gate

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PRE-MERGE QUALITY GATE                          │
├────────────────────────────────────────────────────────────────────────┤
│ 1. make test-unit       ──> 100% Pass (0 regressions)                 │
│ 2. make test-numerics   ──> Zero NaN/Inf on synthetic 65k vocab logits │
│ 3. make test-benchmarks ──> 7/7 Golden Benchmarks Meet Exact Bounds    │
│ 4. make test-gpu-bounds ──> VRAM < 20 GiB across all worker pairs      │
│                                                                        │
│ IF ANY TEST FAILS: Rollback commit immediately; do NOT merge to main.  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Summary & Next Step

This testing framework guarantees:
1. **Mathematical Verification:** We test the exact failure points (TOC dots, sliding window overlaps, FP16 overflow, ESL bias).
2. **Deterministic Confidence:** Every phase of the backend engine has pre-written assertions before code is merged.
3. **Auditability:** Ground-truth test documents are stored directly in the repository for repeatable benchmark runs.
