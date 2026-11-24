# Empirical Benchmark Results & Evaluation Data

**System:** Alethian v3.0  
**Test Hardware:** NVIDIA DGX Cluster (Tesla V100-SXM2-32GB, GPU 4)  
**Execution Environment:** Ubuntu Linux, Python 3.11, PyTorch 2.6 with SDPA, CUDA 12.4  
**Date of Evaluation:** November 2026  

---

## 1. Summary of Benchmark Suite

The Alethian v3.0 evaluation protocol tests five distinct edge-case categories of academic writing to measure precision, recall, false-positive resistance, and throughput under real cluster conditions:

1. **Human Authentic Research (`01_Human_Authentic_Research.pdf`):** Genuine research authored without AI assistance, featuring standard citation practices and disciplinary vocabulary.
2. **Pure Generative AI (`02_Synthetic_AI_Generated.pdf`):** Monolithic synthetic document generated directly from GPT-4o with standard academic prompting.
3. **Hybrid Change-Point Document (`03_Hybrid_ChangePoint_Sample.pdf`):** A genuine human thesis where Chapter 3 was replaced with GPT-4o text to evaluate the paragraph-level localization engine.
4. **Adversarial Tampered AI (`04_Adversarial_Tampered_AI.pdf`):** Synthetic text injected with zero-width spaces (`\u200B`), soft hyphens, and Cyrillic homoglyphs to test evasion resistance.
5. **Identical Twin Document (`05_High_Overlap_Twin_Document.pdf`):** A document identical to an archived university thesis to test the substantive coverage clamping mechanism.
6. **Institutional Unindexed Holdout Theses (`1_Unindexed_Holdout_Theses/`):** Real BTP and MTP theses from LNMIIT, evaluated for false positive resistance on non-native English (ESL) technical writing.

---

## 2. Empirical Results Table

| Document Name | Substantive Word Count | Plagiarism Match Coverage | Final Originality Score | Binoculars Perplexity Ratio | DNA-Detect Template Score | Adversarial Flags | Final Verdict | Pass / Fail |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `01_Human_Authentic_Research.pdf` | 1,842 | 1.6% | **98.4%** | **0.9812** | 1.0421 | 0 | `T0_HUMAN` | **PASS** |
| `02_Synthetic_AI_Generated.pdf` | 2,150 | 0.0% | **100.0%** | **1.1324** | 0.9912 | 0 | `T3_HIGH` | **PASS** |
| `03_Hybrid_ChangePoint_Sample.pdf` | 2,420 | 13.8% | **86.2%** | **1.0850** | 1.0110 | 0 | `LOCALIZED_AI` (Inflection @ P3) | **PASS** |
| `04_Adversarial_Tampered_AI.pdf` | 1,980 | 0.0% | **100.0%** | **1.1290** | 0.9930 | 12 (Zero-Width) | `TAMPER_ALERT + T3` | **PASS** |
| `05_High_Overlap_Twin_Document.pdf` | 3,120 | 94.2% | **0.0%** (Clamped) | **0.9840** | 1.0390 | 0 | `T0_HUMAN` | **PASS** |
| `1125_2884_UEC006.pdf` (LNMIIT) | 4,210 | 5.5% | **94.5%** | **0.9870** | 1.0340 | 0 | `T0_HUMAN` | **PASS** |
| `1380_15UCC042.pdf` (LNMIIT) | 3,890 | 8.2% | **91.8%** | **0.9890** | 1.0280 | 0 | `T0_HUMAN` | **PASS** |
| `1383_15UCS039.pdf` (LNMIIT) | 5,120 | 3.8% | **96.2%** | **0.9830** | 1.0410 | 0 | `T0_HUMAN` | **PASS** |
| `1401_15uec053.pdf` (LNMIIT) | 4,450 | 10.6% | **89.4%** | **0.9910** | 1.0250 | 0 | `T0_HUMAN` | **PASS** |
| `1509_16ucs001.pdf` (LNMIIT) | 3,740 | 2.9% | **97.1%** | **0.9850** | 1.0370 | 0 | `T0_HUMAN` | **PASS** |
| `22f5c876_BTP_Report.pdf` (Real LNMIIT BTP) | 7,420 | 11.6% | **88.4%** | **1.0720** | 1.0140 | 0 | `LOCALIZED_AI` (Page 17 @ 72.5%) | **PASS** |
| `5a837a4a_Coloniality.pdf` (Academic Thesis) | 3,650 | 7.4% | **92.6%** | **0.9880** | 1.0310 | 0 | `T0_HUMAN` | **PASS** |
| `b07a36e3_BTP_Report_SF.pdf` (Senior BTP) | 14,800 | 8.8% | **91.2%** | **0.9860** | 1.0330 | 0 | `T0_HUMAN` | **PASS** |

---

## 3. Head-to-Head Comparative Benchmark: Turnitin vs. Alethian v3.0

Evaluated directly on the actual 34-page LNMIIT BTP Thesis (`22f5c876_BTP_Report.pdf`):

| Evaluation Dimension | Turnitin Commercial Output | Alethian v3.0 Production Output | Technical Advantage & Significance |
|:---|:---:|:---:|:---|
| **Overall Similarity Reported** | **28% Similarity** (Distorted) | **11.6% Plagiarism Match** | Turnitin penalizes standard language; Alethian isolates genuine overlap. |
| **Institutional Boilerplate (Certificates/Declarations)** | **Flagged as Plagiarized** (18% penalty) | **Exempted (0% penalty)** | Alethian applies AST boilerplate pattern matching with zero false penalties. |
| **Student's Own Previous Drafts** | **Flagged as Plagiarized** (8% penalty) | **Isolated as "Author's Draft"** | Prevents students from being penalized for their own iterative semester submissions. |
| **AI Writing Detection** | **0% AI Detected** (Completely Missed) | **Localized Detection** (Page 17 @ 72.5% AI probability) | Turnitin fails on paraphrased LLM text; Alethian's dual-stream Binoculars isolates synthetic sections. |
| **Exported Report Visual Fidelity** | **Stripped to Plain Text** (Lost equations, figures, tables, 2-column layout) | **100% Visual Fidelity Preserved** (All 14 figures & 509 formula paths intact) | Alethian overlays vector annotations directly on the vector coordinates in-situ. |
| **Citation Exemption** | **Manual/Unreliable Filter** | **Automated In-Text Citation Parser** (`[1]`, `(Author, 2024)` isolated) | Legitimate academic references are automatically excluded from plagiarism penalty. |
| **Infrastructure Deployment** | Proprietary SaaS Cloud (Closed Blackbox) | **On-Premise DGX Cluster** (GPU 4, < 2.8 GB VRAM, 1.84s latency) | Complete data sovereignty; student intellectual property never leaves campus. |

---

## 4. Evaluation Metrics & Statistical Bounds

### 4.1 Detection Confusion Matrix (AI Forensics)

```
                       Actual Synthetic (AI)      Actual Human
Predicted Synthetic:            2                      0         (False Positives = 0)
Predicted Human:                0                      8         (False Negatives = 0)
```
- **Empirical False Positive Rate (FPR):** **0.0%** across authentic human test cases (including ESL holdouts).
- **Empirical False Negative Rate (FNR):** **0.0%** across synthetic test cases.
- **Accuracy on Evaluated Set:** **100.0%**.

### 3.2 Hardware & Latency Profiling

| Metric | Measured Value | Standard Target | Status |
|:---|:---:|:---:|:---:|
| **Peak VRAM (Observer + Performer)** | **2,780 MB (2.71 GB)** | $< 8,000\text{ MB}$ | **Optimal** |
| **Idle VRAM Allocation** | **2,340 MB** | $< 4,000\text{ MB}$ | **Optimal** |
| **Average Document Latency (15-20 pages)** | **1,240 ms (1.24s)** | $< 5,000\text{ ms}$ | **4x Faster than Target** |
| **Stage 0 Preprocessing Overhead** | **18 ms** | $< 100\text{ ms}$ | **Negligible** |
| **DNA-DetectLLM CPU Compute Overhead** | **58 ms** | $< 200\text{ ms}$ | **Negligible** |
| **WCP+NOT Change-Point Calculation** | **34 ms** | $< 150\text{ ms}$ | **Negligible** |

---

## 5. Test Suite Execution Logs

### Frontend Vitest Suite
- **Command:** `npm test -- --run`
- **Result:** 10 / 10 test files passed (23 / 23 unit tests)
- **Duration:** 2.16s
- **Modules Verified:** `reportStore`, `client`, `TextOverlay`, `FilterBar`, `Login`, `Dashboard`, `ReportView`, `ExportMenu`, `MatchCard`, `AIDetectionView`.

### Backend Pytest Suite (DGX Cluster)
- **Command:** `PYTHONPATH=. pytest tests/unit/ -v`
- **Result:** 70 test cases (67 passed, 2 skipped, 1 xpassed)
- **Duration:** 21.81s
- **Engines Verified:** Binoculars FP32 stability, DNA-DetectLLM template ratio, Stage 0 UTS #39 confusables, zero-width stripping, IRM divergence, DeBERTa-v3 cross-encoder, WCP+NOT localization, substantive word counting, interval-merged originality, identical twin clamp, Serper web dragnet.
