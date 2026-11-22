# Alethian v3.0: Viva Voce & Defense Q&A Master Reference

This document prepares the project presenters for rigorous technical cross-examination by university faculty, external examiners, and department deans during the BTP project defense.

---

## Technical Domain 1: AI Detection & Autoregressive Mechanics

### Q1.1: "How can you detect text from GPT-4o or Claude 3.5 without ever having trained on their outputs?"
> **Examiner Intent:** Testing whether you understand the fundamental difference between supervised classification (black-box ML) and zero-shot autoregressive statistical inference.  
> 
> **Model Answer:**  
> "Supervised classifiers like RoBERTa or DistilBERT learn superficial surface patterns of a specific training corpus. When a new frontier model is released, its vocabulary and prompt alignment shift, causing supervised accuracy to collapse.
> 
> Alethian does not train a classifier. Instead, we exploit a fundamental property common to **all** autoregressive language models: mode-seeking token generation. Modern LLMs select tokens that maximize probability under their learned parameters:
> $$p(x_t \mid x_{<t}) = \text{softmax}\left(\frac{W \cdot h_t}{\tau}\right)$$
> This creates an unnatural statistical regularity—a 'smoothness' in cross-entropy across token sequences. Human writing, in contrast, exhibits high 'burstiness', alternating between creative, high-surprise phrases and formulaic connectors. By evaluating the ratio between perplexity and cross-perplexity using our paired Qwen2.5 observer and performer models, we detect this mode-seeking signature without needing any proprietary training data."

---

### Q1.2: "Explain the mathematical intuition behind the Binoculars formula. Why is it a ratio rather than raw perplexity?"
> **Examiner Intent:** Probing whether you simply copied the Binoculars formula or understand why raw perplexity fails.  
> 
> **Model Answer:**  
> "Raw perplexity measures the surprise of a single model:
> $$\text{PPL}(s) = \exp\left(-\frac{1}{N}\sum_{i=1}^N \log p(t_i \mid t_{<i})\right)$$
> Raw perplexity alone is useless as a universal detector because domain-specific technical prose (like medical or legal literature) naturally has very low perplexity due to restricted vocabulary. A raw perplexity threshold would falsely flag thousands of genuine academic papers.
> 
> Binoculars solves this by taking the ratio of performer perplexity to cross-perplexity:
> $$\text{Binoculars}(s) = \frac{\log \text{PPL}_{M_{\text{perf}}}(s)}{\log \text{xPPL}_{M_{\text{obs}}, M_{\text{perf}}}(s)}$$
> The numerator evaluates how unsurprised the instruction-tuned model is by the actual sequence tokens. The denominator evaluates how well the observer's probability distribution over the *entire vocabulary* aligns with the performer.
> For human text, the actual tokens have moderate surprise while the overall vocabulary alignment is typical, yielding a ratio $< 1.01$. For synthetic text, the actual tokens are chosen near the distribution peaks (low PPL), driving the ratio $\ge 1.07$."

---

### Q1.3: "Why doesn't your system flag non-native English (ESL) students who write in simple, repetitive English?"
> **Examiner Intent:** Checking for algorithmic fairness and knowledge of the Stanford 2023 study demonstrating ESL bias in commercial tools.  
> 
> **Model Answer:**  
> "A prominent 2023 study by Liang et al. demonstrated that commercial detectors (Turnitin, GPTZero) falsely flag over 60% of US TOEFL essays written by non-native students because simple grammar yields low perplexity.
> 
> In Alethian, the Binoculars ratio provides a mathematical self-normalizing invariant:
> When an ESL author writes using simple sentence connectors ('furthermore', 'it is clear that'), **both** the numerator (performer perplexity) and denominator (cross-perplexity) decrease proportionally. The performer finds the simple words predictable, but the observer also assigns high probability to those exact simple words. Because both terms drop at the same rate:
> $$\frac{\downarrow \log \text{PPL}_{\text{perf}}}{\downarrow \log \text{xPPL}_{\text{obs, perf}}} \approx 1.0$$
> The ratio remains stable within the human tier ($< 1.01$). In our empirical tests on authentic LNMIIT unindexed engineering theses, we observed a 0.0% false positive rate."

---

## Technical Domain 2: Systems Engineering & Scalability

### Q2.1: "Why did you split the Celery worker into two separate processes (`celery_worker` and `celery_ai_worker`)?"
> **Examiner Intent:** Testing your understanding of concurrency, GPU memory management, and asynchronous system design.  
> 
> **Model Answer:**  
> "If a single worker handles both PDF parsing, database I/O, and GPU inference, two severe problems arise:
> 1. **CUDA Deadlocks & Memory Leaks:** Celery's default `prefork` pool uses process forking. When a child process forks after PyTorch initializes CUDA contexts, CUDA drivers frequently deadlock or corrupt memory.
> 2. **Head-of-Line Blocking:** A slow, 100-page OCR PDF extraction job would block the GPU from running neural inference for waiting documents.
> 
> We resolved this by creating two dedicated services:
> - `celery_worker`: Runs with `--concurrency=2` prefork pool on CPU, handling non-blocking file parsing, shingling, and web crawling.
> - `celery_ai_worker`: Dedicated exclusively to GPU 4, configured with `--pool=solo`. This ensures a single persistent Python thread owns the GPU memory context, keeping the Qwen2.5 weights pinned permanently in VRAM without fork overhead."

---

### Q2.2: "How much GPU memory does Alethian require, and how does it scale across multiple student submissions?"
> **Examiner Intent:** Probing resource feasibility and cluster infrastructure limits.  
> 
> **Model Answer:**  
> "In Version 2, the proposed Falcon-7B model pair required 28 GB of VRAM, which saturated an entire Tesla V100 GPU and limited batching.
> In Version 3, we migrated to the `Qwen2.5-0.5B` observer and performer pair loaded in FP16 with PyTorch Scaled Dot-Product Attention (SDPA). This consumes only **2.78 GB of VRAM** total.
> 
> Because a 32 GB V100 or 80 GB A100 GPU has over 25 GB of headroom remaining, the AI worker can process batched token windows concurrently. On our DGX cluster, a complete 20-page thesis evaluates in just 1.24 seconds, allowing a single GPU to process over 2,800 full dissertations per hour."

---

## Technical Domain 3: Plagiarism & String Matching

### Q3.1: "How did you fix the Table of Contents dot leader flaw that inflated plagiarism scores in legacy engines?"
> **Examiner Intent:** Verifying that you addressed real-world thesis formatting challenges.  
> 
> **Model Answer:**  
> "Standard text extraction splits documents into whitespace tokens. In institutional theses, the Table of Contents often contains strings like `. . . . . . . . . . 12` representing dot leaders and page numbers. If two theses use the same LaTeX template, legacy engines count those dot sequences as identical matched words, unfairly inflating the plagiarism percentage.
> 
> We resolved this by introducing our substantive word counter:
> ```python
> def _count_substantive_words(text: str) -> int:
>     if not text or not any(c.isalpha() for c in text):
>         return 0
>     return sum(1 for w in text.split() if any(c.isalnum() for c in w))
> ```
> If a passage contains zero alphabetic characters, it is assigned 0 substantive words. The originality denominator only counts authentic scholarly prose."

---

### Q3.2: "What is 1D Interval Merging, and why is it necessary for shingling algorithms?"
> **Examiner Intent:** Testing algorithmic rigor in string metric calculation.  
> 
> **Model Answer:**  
> "When matching documents using $k$-grams (we use $k=6$ words), overlapping windows are generated. If a 10-word sentence matches an existing source, it generates five overlapping 6-gram matches.
> If an engine simply sums the length of each matched shingle:
> $$6 + 6 + 6 + 6 + 6 = 30 \text{ matched words (for a 10-word sentence!)}$$
> This double-counting artificially inflates plagiarism scores.
> 
> Alethian maps each match to its character span $[s_i, e_i]$ in the submitted document. We then apply 1D Interval Merging (sorting spans by start index and merging overlapping boundaries). The coverage is computed strictly on the union of disjoint spans:
> $$\text{Merged} = \bigcup [s_i, e_i]$$
> This mathematically guarantees that no word is ever counted more than once."

---

### Q3.3: "How does the system catch identical clone documents when minor changes like student names are made?"
> **Examiner Intent:** Checking edge-case robustness against twin document submissions.  
> 
> **Model Answer:**  
> "When a student submits an identical copy of another student's thesis but modifies the title page and acknowledgment section, raw match coverage might reach 88% rather than 100%. A superficial score of 12% originality is misleading because the thesis is fundamentally plagiarized.
> 
> Alethian implements an **85% Substantive Coverage Clamp**:
> If the interval-merged substantive match coverage exceeds 85%, the engine clamps the originality score strictly to **0.0%**. This ensures that blatant academic fraud is clearly flagged without ambiguity."

---

## Technical Domain 4: Adversarial Attacks & Defense

### Q4.1: "A student injects zero-width non-joiners (`\u200C`) between every syllable in ChatGPT-generated text. What happens?"
> **Examiner Intent:** Evaluating knowledge of NLP evasion techniques.  
> 
> **Model Answer:**  
> "This is a known zero-width tokenization fragmentation attack. By inserting `\u200C` or `\u200B` between letters (e.g., `M\u200Bodel`), standard tokenizers break the word into individual character tokens, completely destroying n-gram and vector matching.
> 
> Alethian's **Stage 0 Preprocessor** runs an automated regex filter before tokenization:
> ```python
> re.sub(r'[\u200B-\u200D\uFEFF\u00AD]', '', text)
> ```
> It strips all zero-width and invisible formatting characters. Furthermore, if the count of stripped invisible characters exceeds five, the engine attaches a high-severity `TAMPER_ALERT` to the faculty report. The document is then tokenized normally and flagged as synthetic AI."

---

### Q4.2: "What if a student substitutes English 'a', 'e', and 'o' with lookalike Cyrillic characters?"
> **Examiner Intent:** Testing homoglyph attack resistance.  
> 
> **Model Answer:**  
> "In Unicode, Cyrillic small letter 'а' (`\u0430`) is visually identical to Latin 'a' (`\u0061`), but has a different byte sequence.
> Stage 0 passes all input text through the **Unicode Technical Standard #39 (UTS #39) Confusable Mapping Specification**. Every confusable glyph is normalized to its canonical Latin ASCII equivalent before passing to our shinglers and language models. The student's substitution has zero impact on detection."
