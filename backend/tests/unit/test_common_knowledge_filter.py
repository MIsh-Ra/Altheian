"""
Unit tests for the Academic Common Domain Knowledge & Polyglot Syntax Filter (Alethian v3.2).
Validates:
1. Academic Formulas List (AFL) & Springer Nature phrasebank detection.
2. Polyglot code syntax (Python, C/C++, Java, JS/TS, SQL, Bash) and LaTeX math detection.
3. Empirical results and metric table detection.
4. Comprehensive chunk triage via should_skip_from_web_search().
5. Preserves genuine narrative prose and does not over-filter potential plagiarism.
"""
import pytest
from app.core.common_knowledge_filter import (
    is_academic_formulaic_chunk,
    is_code_or_math_chunk,
    is_empirical_results_chunk,
    should_skip_from_web_search,
)


def test_academic_formulaic_chunk_detection():
    # Formulaic transition/hedging academic phrases
    formulaic_text = (
        "In order to examine the relationship between model depth and latency, "
        "as can be seen from the following results, it is important to note that "
        "the findings of the present study suggest that further research is needed. "
        "On the other hand, the vast majority of prior work has demonstrated that "
        "it should be emphasized that there is a significant difference."
    )
    assert is_academic_formulaic_chunk(formulaic_text) is True

    # Genuine novel narrative / substantive domain content
    genuine_text = (
        "We developed a novel dual-stream perceptual hashing framework called PhashShield. "
        "Unlike prior works that rely on static discrete cosine transforms, our model "
        "embeds high-frequency spatial gradients into a 128-dimensional quantized lattice "
        "which preserves semantic invariance under aggressive Gaussian blur and JPEG compression."
    )
    assert is_academic_formulaic_chunk(genuine_text) is False


def test_code_syntax_python_detection():
    python_snippet = """
    def train_epoch(model, dataloader, optimizer, criterion):
        model.train()
        total_loss = 0.0
        for batch_idx, (inputs, targets) in enumerate(dataloader):
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        return total_loss / len(dataloader)
    """
    assert is_code_or_math_chunk(python_snippet) is True


def test_code_syntax_cpp_java_detection():
    cpp_snippet = """
    #include <iostream>
    #include <vector>
    using namespace std;

    template <typename T>
    void quicksort(std::vector<T>& arr, int low, int high) {
        if (low < high) {
            int pi = partition(arr, low, high);
            quicksort(arr, low, pi - 1);
            quicksort(arr, pi + 1, high);
        }
    }
    """
    assert is_code_or_math_chunk(cpp_snippet) is True


def test_code_syntax_javascript_typescript():
    js_snippet = """
    import React, { useState, useEffect } from 'react';
    
    export const useDebounce = <T,>(value: T, delay: number): T => {
        const [debouncedValue, setDebouncedValue] = useState<T>(value);
        useEffect(() => {
            const timer = setTimeout(() => setDebouncedValue(value), delay);
            return () => clearTimeout(timer);
        }, [value, delay]);
        return debouncedValue;
    };
    """
    assert is_code_or_math_chunk(js_snippet) is True


def test_code_syntax_sql_and_bash():
    sql_snippet = """
    SELECT user_id, COUNT(submission_id) AS total_submissions,
           AVG(similarity_score) AS avg_score
    FROM submissions
    WHERE created_at >= NOW() - INTERVAL '30 days'
    GROUP BY user_id
    HAVING COUNT(submission_id) > 5
    ORDER BY avg_score DESC;
    """
    assert is_code_or_math_chunk(sql_snippet) is True

    bash_snippet = """
    #!/bin/bash
    set -euo pipefail
    for file in $(ls *.pdf); do
        echo "Processing $file..."
        python3 extract_text.py --input "$file" --output "${file%.pdf}.txt"
    done
    """
    assert is_code_or_math_chunk(bash_snippet) is True


def test_latex_math_detection():
    math_snippet = """
    The loss function is formally formulated as:
    \\mathcal{L}_{total} = \\alpha \\sum_{i=1}^N \\| y_i - \\hat{y}_i \\|^2 + \\beta \\mathbb{E}_{x \\sim p_{data}} [\\log D(x)]
    where \\nabla_\\theta \\mathcal{J}(\\theta) represents the stochastic gradient evaluated at convergence.
    """
    assert is_code_or_math_chunk(math_snippet) is True


def test_empirical_results_chunk_detection():
    # Model evaluation metrics / ablation tables
    results_chunk = """
    Table 3.4: Comparative evaluation across benchmark architectures.
    Model              Accuracy (%)    Precision    Recall    F1-Score
    ResNet-50          89.4           0.88         0.89      0.885
    EfficientNet-B4    92.1           0.91         0.93      0.920
    Vision Transformer 94.7           0.94         0.95      0.945
    Ours (Hybrid)      96.2           0.96         0.97      0.965
    p-value < 0.001 with 95% CI across 5-fold cross-validation.
    """
    assert is_empirical_results_chunk(results_chunk) is True


def test_should_skip_from_web_search_btp_false_positive_cases():
    # Exact snippet from BTP match #14 (PyTorch random tensor debug code)
    btp_match_14 = """
    To verify convergence, we initialize synthetic tensors using torch.randn(32, 512, device='cuda')
    and evaluate the output norm:
    torch.nn.functional.cross_entropy(logits, labels).backward()
    assert not torch.isnan(loss).any(), "NaN loss detected in forward pass"
    """
    should_skip, reason = should_skip_from_web_search(btp_match_14)
    assert should_skip is True
    assert "Code syntax" in reason

    # Exact snippet from BTP match #6 (Table 3.4 false premise rejection results)
    btp_match_6 = """
    Table 3.4 summarizes the false-premise rejection rate across tasks:
    Task A: accuracy=78.2%, precision=0.81, recall=0.75, F1=0.78, p < 0.05
    Task B: accuracy=84.6%, precision=0.86, recall=0.83, F1=0.84, p < 0.01
    Task C: accuracy=91.0%, precision=0.92, recall=0.90, F1=0.91, p < 0.001
    """
    should_skip, reason = should_skip_from_web_search(btp_match_6)
    assert should_skip is True
    assert "empirical results" in reason.lower()

    # Substantive unsourced student writing that SHOULD be analyzed
    real_student_writing = """
    The distributed coordinator employs a consensus protocol derived from Raft, but modifies
    the leader election mechanism to prioritize nodes with lower network latency and higher
    available memory. When a leader heartbeat fails, followers broadcast election requests
    containing their current hardware utilization scores along with their log index.
    """
    should_skip, reason = should_skip_from_web_search(real_student_writing)
    assert should_skip is False
    assert reason is None
