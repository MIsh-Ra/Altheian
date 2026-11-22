# Alethian v3.0 — AI Detection Implementation Plan

**Author:** AI Systems Engineering  
**Date:** 2026-11-22  
**Status:** Ready for Execution  
**Prerequisite:** All v2.0 plagiarism engine bugs (scoring, heatmap, print, Serper) must be fixed first (Phase 0).

---

## Phase 0: v2.0 Bug Fixes (Pre-Requisite)

> [!IMPORTANT]
> These fixes must be applied and verified before beginning AI detection work, as they affect the shared text extraction and report engine.

### 0.1 Scoring Fix — `report_engine.py`

**File:** `Alethian/backend/app/core/report_engine.py`  
**Function:** `calculate_originality()`

```python
# Replace matched_words = total_matched_chars / 6.0 with:
def _count_substantive_words(text: str) -> int:
    """Count words containing at least one alphanumeric character."""
    return sum(1 for w in text.split() if any(c.isalnum() for c in w))

# In calculate_originality():
# Use substantive word count for denominator instead of raw split()
doc_substantive_words = _count_substantive_words(doc_text)
# Count actual words in merged match intervals
matched_words = sum(_count_substantive_words(doc_text[s:e]) for s, e in merged)
coverage = matched_words / max(1, doc_substantive_words)
```

### 0.2 Heatmap Fix — `report_engine.py`

**Function:** `generate_heatmap()`  
Merge per-page match intervals before computing density to prevent overcounting from overlapping sliding windows.

### 0.3 Print Fix — `frontend/src/index.css`

Add `@media print` rules to override `h-screen`, `overflow-hidden` containers.

### 0.4 Serper Key Persistence — `admin.py`

Save `serper_api_key` to Redis `config:serper_api_key` in the PATCH handler.

**Verification:** Re-run the twin document test (`15UCS032-19.pdf`). Score must be ≥ 99%.

---

## Phase 1: Infrastructure & Model Setup (Day 1–2)

### 1.1 Download Foundation Models to DGX

```bash
# SSH into DGX
ssh ak-dgx

# Activate the backend environment
source /home/23ucs529/alethian_backend_env/bin/activate

# Create model cache directory
mkdir -p /home/23ucs529/.cache/huggingface/hub

# Download Stage 1 models (Falcon-7B pair)
python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
for model_id in ['tiiuae/falcon-7b', 'tiiuae/falcon-7b-instruct']:
    print(f'Downloading {model_id}...')
    AutoTokenizer.from_pretrained(model_id)
    AutoModelForCausalLM.from_pretrained(model_id, torch_dtype='float16')
    print(f'  ✓ {model_id} cached')
"

# Download Stage 2 models (Llama-3-8B pair + DeBERTa)
python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModelForSequenceClassification
for model_id in ['meta-llama/Meta-Llama-3-8B', 'meta-llama/Meta-Llama-3-8B-Instruct']:
    print(f'Downloading {model_id}...')
    AutoTokenizer.from_pretrained(model_id)
    AutoModelForCausalLM.from_pretrained(model_id, torch_dtype='float16')

print('Downloading DeBERTa academic detector...')
AutoTokenizer.from_pretrained('desklib/ai-text-detector-academic-v1.01')
AutoModelForSequenceClassification.from_pretrained('desklib/ai-text-detector-academic-v1.01')
"
```

**Estimated download:** ~60 GB total. ~30 min on DGX network.

### 1.2 Create AI Detection Package Structure

```bash
# On local machine
mkdir -p Alethian/backend/app/core/ai_detection
touch Alethian/backend/app/core/ai_detection/__init__.py
touch Alethian/backend/app/core/ai_detection/preprocessor.py
touch Alethian/backend/app/core/ai_detection/binoculars.py
touch Alethian/backend/app/core/ai_detection/dna_detect.py
touch Alethian/backend/app/core/ai_detection/escalation.py
touch Alethian/backend/app/core/ai_detection/localization.py
touch Alethian/backend/app/core/ai_detection/model_manager.py
touch Alethian/backend/app/core/ai_detection/schemas.py
touch Alethian/backend/celery_ai_worker.py
```

### 1.3 Add Python Dependencies

```bash
# On DGX (alethian_backend_env already has torch + transformers)
# Verify existing:
pip list | grep -E "torch|transformers|accelerate"

# Add only missing deps:
pip install unicodedata2 regex scipy
```

### 1.4 Database Migration

```sql
-- Run on DGX PostgreSQL
ALTER TABLE reports ADD COLUMN ai_detection_id VARCHAR REFERENCES ai_detection_results(id);

CREATE TABLE ai_detection_results (
    id                  VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    report_id           VARCHAR REFERENCES reports(id),
    binoculars_score    FLOAT,
    dna_detect_score    FLOAT,
    stage1_model_pair   VARCHAR,
    escalated           BOOLEAN DEFAULT FALSE,
    llama_binoculars_score FLOAT,
    llama_dna_score     FLOAT,
    irm_score           FLOAT,
    deberta_probability FLOAT,
    stage2_model_pair   VARCHAR,
    verdict_tier        VARCHAR NOT NULL,
    confidence          FLOAT,
    abstained           BOOLEAN DEFAULT FALSE,
    tamper_alert        BOOLEAN DEFAULT FALSE,
    stage1_latency_ms   INTEGER,
    stage2_latency_ms   INTEGER,
    total_latency_ms    INTEGER,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ai_detection_windows (
    id              VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    result_id       VARCHAR REFERENCES ai_detection_results(id),
    window_index    INTEGER,
    char_start      INTEGER,
    char_end        INTEGER,
    page_number     INTEGER,
    binoculars_score    FLOAT,
    dna_detect_score    FLOAT,
    is_ai_segment       BOOLEAN,
    UNIQUE(result_id, window_index)
);

CREATE INDEX idx_ai_results_report ON ai_detection_results(report_id);
CREATE INDEX idx_ai_windows_result ON ai_detection_windows(result_id);
```

---

## Phase 2: Stage 0 — Text Preprocessor (Day 2–3)

### 2.1 `preprocessor.py` — Core Functions

```python
# Alethian/backend/app/core/ai_detection/preprocessor.py

from pydantic import BaseModel, Field
from typing import Optional
import re
import unicodedata


class PreprocessResult(BaseModel):
    """Result of Stage 0 text preprocessing."""
    cleaned_text: str
    prose_token_count: int
    abstain: bool = False
    abstain_reason: Optional[str] = None
    tamper_alert: bool = False
    tamper_count: int = 0
    tamper_details: list[str] = Field(default_factory=list)
    latex_regions_masked: int = 0


CONFUSABLE_MAP: dict[str, str] = {
    '\u0410': 'A', '\u0412': 'B', '\u0421': 'C', '\u0415': 'E',  # Cyrillic
    '\u041d': 'H', '\u041a': 'K', '\u041c': 'M', '\u041e': 'O',
    '\u0420': 'P', '\u0422': 'T', '\u0425': 'X',
    '\u200b': '',   # Zero-width space
    '\u200c': '',   # Zero-width non-joiner
    '\u200d': '',   # Zero-width joiner
    '\u2060': '',   # Word joiner
    '\ufeff': '',   # BOM / zero-width no-break space
}


def detect_unicode_tampering(text: str) -> tuple[str, int, list[str]]:
    """UTS #39 confusable mapping + invisible character removal."""
    details = []
    count = 0
    cleaned_chars = []
    
    for ch in text:
        if ch in CONFUSABLE_MAP:
            replacement = CONFUSABLE_MAP[ch]
            cleaned_chars.append(replacement)
            count += 1
            details.append(f"U+{ord(ch):04X} '{ch}' → '{replacement}'")
        elif unicodedata.category(ch) in ('Cf', 'Mn', 'Cc') and ch not in '\n\r\t ':
            count += 1
            details.append(f"U+{ord(ch):04X} (invisible: {unicodedata.name(ch, 'UNKNOWN')})")
        else:
            cleaned_chars.append(ch)
    
    return ''.join(cleaned_chars), count, details


def mask_latex_and_math(text: str) -> tuple[str, int]:
    """Replace LaTeX environments and inline math with [MATH] tokens."""
    patterns = [
        r'\\begin\{equation\*?\}.*?\\end\{equation\*?\}',
        r'\\begin\{align\*?\}.*?\\end\{align\*?\}',
        r'\$\$.*?\$\$',
        r'\$[^$]+\$',
        r'\\[a-zA-Z]+\{[^}]*\}',
    ]
    count = 0
    for pat in patterns:
        matches = re.findall(pat, text, re.DOTALL)
        count += len(matches)
        text = re.sub(pat, ' [MATH] ', text, flags=re.DOTALL)
    return text, count


def mask_citations(text: str) -> str:
    """Replace parenthetical citations with [CIT] tokens."""
    text = re.sub(r'\([A-Z][a-z]+(?:\s+(?:et\s+al\.?|&)\s+[A-Z][a-z]+)*,?\s*\d{4}[a-z]?\)', ' [CIT] ', text)
    text = re.sub(r'\[\d+(?:[-–,]\s*\d+)*\]', ' [CIT] ', text)
    return text


def normalize_pdf_line_wraps(text: str) -> str:
    """Rejoin hyphenated line breaks and hard-wrapped lines."""
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    text = re.sub(r'(?<=[a-z,;])\n(?=[a-z])', ' ', text)
    return text


def count_prose_tokens(text: str) -> int:
    """Count substantive prose tokens (not punctuation or [MASK] tokens)."""
    return sum(1 for w in text.split() 
               if any(c.isalnum() for c in w) and w not in ('[MATH]', '[CIT]'))


def preprocess_for_ai_detection(raw_text: str, min_tokens: int = 150) -> PreprocessResult:
    """Full Stage 0 preprocessing pipeline."""
    # Step 1: Unicode tampering detection
    cleaned, tamper_count, tamper_details = detect_unicode_tampering(raw_text)
    tamper_alert = tamper_count > 3
    
    # Step 2: PDF line-wrap normalization
    cleaned = normalize_pdf_line_wraps(cleaned)
    
    # Step 3: LaTeX/Math masking
    cleaned, latex_count = mask_latex_and_math(cleaned)
    
    # Step 4: Citation masking
    cleaned = mask_citations(cleaned)
    
    # Step 5: Whitespace normalization
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Step 6: Prose token count + abstention check
    token_count = count_prose_tokens(cleaned)
    abstain = token_count < min_tokens
    
    return PreprocessResult(
        cleaned_text=cleaned,
        prose_token_count=token_count,
        abstain=abstain,
        abstain_reason=f"Insufficient prose tokens ({token_count} < {min_tokens})" if abstain else None,
        tamper_alert=tamper_alert,
        tamper_count=tamper_count,
        tamper_details=tamper_details[:20],
        latex_regions_masked=latex_count,
    )
```

---

## Phase 3: Stage 1 — Binoculars + DNA-DetectLLM Engine (Day 3–6)

### 3.1 `model_manager.py` — GPU-Pinned Model Singleton

```python
# Key design: Models loaded once at worker startup, pinned to specific GPUs.
# Uses FP16 weights + SDPA attention (not FlashAttention) for Volta V100.

class ModelManager:
    """Singleton GPU model loader for AI detection inference."""
    
    _instance = None
    
    def __init__(self, observer_gpu: int, performer_gpu: int, model_pair: str):
        self.observer_gpu = observer_gpu
        self.performer_gpu = performer_gpu
        self.model_pair = model_pair
        # Load with: torch_dtype=torch.float16, attn_implementation="sdpa"
        # Tokenizer: shared between observer and performer (same vocab)
```

### 3.2 `binoculars.py` — Core Metric

The Binoculars score is computed as:

$$\text{Binoculars}(s) = \frac{\log \text{PPL}_{M_{\text{perf}}}(s)}{\log \text{xPPL}_{M_{\text{obs}}, M_{\text{perf}}}(s)}$$

Where:
- $\text{PPL}_{M}(s) = \exp\left(-\frac{1}{N}\sum_{i=1}^{N} \log p_{M}(t_i | t_{<i})\right)$ is standard perplexity
- $\text{xPPL}_{M_1, M_2}(s) = \exp\left(-\frac{1}{N}\sum_{i=1}^{N} \sum_{v} p_{M_1}(v | t_{<i}) \cdot \log p_{M_2}(v | t_{<i})\right)$ is cross-perplexity

**Implementation:**
1. Single forward pass through both models produces logits.
2. Upcast logits to `torch.float32` before `F.log_softmax`.
3. Compute both PPL and xPPL from the same logits tensors.
4. DNA-DetectLLM template ratio computed simultaneously (zero extra GPU cost).

### 3.3 Sliding Window Strategy

```
Document text (10,000 tokens)
├── Window 1: tokens[0:512]        → Binoculars score, DNA score
├── Window 2: tokens[256:768]      → Binoculars score, DNA score  (stride=256)
├── Window 3: tokens[512:1024]     → Binoculars score, DNA score
├── ...
└── Window N: tokens[-512:]        → Binoculars score, DNA score

Aggregate: median of all window scores → document-level score
Per-window: used for paragraph-level heatmap
```

### 3.4 Decision Thresholds (From Research Report)

| Binoculars Score Range | Verdict Tier | Action |
| :--- | :--- | :--- |
| ≥ 0.9015 | **T0: Consistent with Human** | Complete. No alert. |
| 0.8536 – 0.9015 | **T1: Indeterminate** | Log but no alert. No accusation. |
| < 0.8536 | **Escalate to Stage 2** | Run Llama-3-8B + DeBERTa audit. |

After Stage 2 escalation:

| Combined Evidence | Verdict Tier |
| :--- | :--- |
| All 4 metrics agree "human" | **T0: Human** |
| Mixed signals, DeBERTa < 0.5 | **T1: Indeterminate** |
| 2+ metrics flag AI, DeBERTa 0.5–0.8 | **T2: Mixed/Partially AI** |
| 3+ metrics flag AI, DeBERTa > 0.8 | **T3: AI-Generated** |

---

## Phase 4: Stage 2 — Escalation Audit (Day 6–8)

### 4.1 `escalation.py`

Only invoked when Stage 1 Binoculars score falls below the indeterminate threshold (< 0.8536).

**Components:**
1. **Llama-3-8B Binoculars** — Second independent model pair for confirmation.
2. **Llama-3-8B DNA-DetectLLM** — Template divergence ratio.
3. **Implicit Reward Model (IRM)** — Extracted from Llama-3-8B-Instruct's internal reward signal.
4. **DeBERTa-v3 Academic Classifier** — `desklib/ai-text-detector-academic-v1.01` as auxiliary binary signal.

> [!WARNING]
> DeBERTa-v3 must run in `torch.float32` due to known FP16 numerical instability in the DeBERTa architecture. At 0.4B parameters, it only consumes ~1.4 GB VRAM in FP32.

### 4.2 `localization.py` — WCP+NOT Change-Point Detection

Identifies boundaries within a document where writing transitions from human to AI-generated (or vice versa).

**Algorithm:**
1. Compute per-window Binoculars scores across the document.
2. Apply Weighted CUSUM (WCP) to detect cumulative score drift.
3. Apply Narrowest-Over-Thresholding (NOT) to pinpoint transition boundaries.
4. Output: list of `(char_start, char_end, is_ai_segment)` intervals.

---

## Phase 5: Integration, API & Frontend (Day 8–12)

### 5.1 Celery AI Worker Configuration

```python
# celery_ai_worker.py — Dedicated worker for AI detection queue
# Launch command:
# CUDA_VISIBLE_DEVICES=1,3 celery -A celery_ai_worker worker \
#     --pool=solo --queues=ai_detection --concurrency=1 \
#     --hostname=ai-primary@%h

# For Stage 2 escalation worker:
# CUDA_VISIBLE_DEVICES=6,7 celery -A celery_ai_worker worker \
#     --pool=solo --queues=ai_escalation --concurrency=1 \
#     --hostname=ai-escalation@%h
```

> [!IMPORTANT]
> Workers MUST use `--pool=solo` (not `prefork`). PyTorch CUDA contexts cannot survive `fork()` — the CUDA runtime will crash with `RuntimeError: Cannot re-initialize CUDA in forked subprocess`.

### 5.2 API Endpoint Extensions

```python
# In reports.py — extend GET /reports/{id}
# Add ai_detection field to ReportDetailResponse schema

# New endpoint:
# GET /api/v1/reports/{id}/ai-detection
# Returns full AI detection result with per-window scores
```

### 5.3 Frontend Extensions

| Component | Change |
| :--- | :--- |
| `ScoreHeader.jsx` | Add AI Detection badge alongside plagiarism score |
| `Heatmap.jsx` | Dual-layer: plagiarism density (existing) + AI probability overlay (new) |
| `ReportView.jsx` | New AI Detection tab/section in the inspector pane |
| `Dashboard.jsx` | AI detection status column in document list |

### 5.4 Config Extensions

```python
# In config.py
AI_DETECTION_ENABLED: bool = True
AI_STAGE1_OBSERVER: str = "tiiuae/falcon-7b"
AI_STAGE1_PERFORMER: str = "tiiuae/falcon-7b-instruct"
AI_STAGE2_OBSERVER: str = "meta-llama/Meta-Llama-3-8B"
AI_STAGE2_PERFORMER: str = "meta-llama/Meta-Llama-3-8B-Instruct"
AI_DEBERTA_MODEL: str = "desklib/ai-text-detector-academic-v1.01"
AI_WINDOW_SIZE: int = 512          # Tokens per analysis window
AI_WINDOW_STRIDE: int = 256        # Stride between windows
AI_MIN_PROSE_TOKENS: int = 150     # Abstention floor
AI_T0_THRESHOLD: float = 0.9015   # Score ≥ this → Human
AI_ESCALATION_THRESHOLD: float = 0.8536  # Score < this → Escalate
```

---

## Testing Strategy

### Unit Tests

| Test | File | Assertion |
| :--- | :--- | :--- |
| Unicode tamper detection | `test_preprocessor.py` | Detects ≥ 3 Cyrillic homoglyphs → `tamper_alert=True` |
| LaTeX masking | `test_preprocessor.py` | `\begin{equation}...` replaced with `[MATH]` |
| Abstention gate | `test_preprocessor.py` | 100-token input → `abstain=True` |
| Binoculars computation | `test_binoculars.py` | Known GPT-4 output scores < 0.85; known human text scores > 0.90 |
| FP16 logit upcast | `test_binoculars.py` | No `NaN` or `Inf` in output for 65k-vocab models |
| WCP+NOT localization | `test_localization.py` | Correctly identifies human→AI transition in synthetic hybrid doc |

### Integration Tests

| Test | Method |
| :--- | :--- |
| **Golden Positive** | Submit known ChatGPT-generated essay → expect Tier T3 |
| **Golden Negative** | Submit verified human thesis from holdout set → expect Tier T0 |
| **Mixed Document** | Submit doc with AI intro + human body → expect T2 + correct window localization |
| **ESL Document** | Submit non-native English thesis → expect T0 (no false positive) |
| **Short Document** | Submit abstract-only (80 tokens) → expect `abstained=True` |
| **Tampered Document** | Submit doc with Cyrillic 'А' replacing Latin 'A' → expect `tamper_alert=True` |

---

## Timeline Summary

| Phase | Days | Deliverable |
| :--- | :--- | :--- |
| **Phase 0** | 1 | v2.0 bug fixes (scoring, heatmap, print, Serper) |
| **Phase 1** | 2 | Model downloads, package structure, DB migration |
| **Phase 2** | 1 | Stage 0 preprocessor (tamper, LaTeX, abstention) |
| **Phase 3** | 3 | Stage 1 Binoculars + DNA-DetectLLM engine |
| **Phase 4** | 2 | Stage 2 escalation audit + WCP+NOT localization |
| **Phase 5** | 4 | API integration, Celery workers, frontend, testing |
| **Total** | **~13 days** | Full AI detection feature shipped and verified |
