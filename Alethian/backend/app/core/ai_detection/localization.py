"""
Change-Point Localization Engine:
- Weighted CUSUM + Narrowest-Over-Thresholding (WCP+NOT) for detecting transitions
  between human and AI-generated sections in documents.
- Paragraph risk gradient mapping from window score intervals to document character
  offsets for frontend heatmap rendering [(start, end, score, is_ai)].
"""

import re
from typing import Any

import numpy as np


class ChangePointDetector:
    """
    Localizes transitions between human-authored and AI-generated text using
    Weighted CUSUM (WCP) and Narrowest-Over-Thresholding (NOT) recursion.
    """

    def __init__(self, default_ai_threshold: float = 0.8536) -> None:
        self.default_ai_threshold = default_ai_threshold

    @staticmethod
    def estimate_noise_sigma(series: np.ndarray) -> float:
        """
        Robust noise scale estimation via Median Absolute Deviation (MAD) of first differences:
            sigma_hat = median(|dX - median(dX)|) / (0.6745 * sqrt(2))
        Insulates variance estimation against step-change contamination.
        """
        if len(series) < 2:
            return 1.0

        diffs = np.diff(series)
        med_diff = float(np.median(diffs))
        mad = float(np.median(np.abs(diffs - med_diff)))
        # Normalize MAD for standard normal distribution of differences (std = sqrt(2) * sigma)
        sigma = mad / (0.6745 * np.sqrt(2.0))

        if sigma < 1e-5:
            sigma = float(np.std(series))
        if sigma < 1e-5:
            sigma = 1.0

        return sigma

    def compute_cusum_contrast(
        self,
        series: np.ndarray,
        s: int,
        t: int,
        e: int,
        sigma: float | None = None,
    ) -> float:
        """
        Computes the studentized weighted CUSUM contrast for split point t in interval [s, e):
            C(s, t, e) = (1 / sigma) * sqrt((n1 * n2) / n) * |mean(X[s:t]) - mean(X[t:e])|
        where n1 = t - s, n2 = e - t, n = e - s.
        """
        n1 = t - s
        n2 = e - t
        n = e - s
        if n1 <= 0 or n2 <= 0 or n <= 0:
            return 0.0

        mean1 = float(np.mean(series[s:t]))
        mean2 = float(np.mean(series[t:e]))
        weight = np.sqrt((n1 * n2) / n)
        raw_contrast = weight * abs(mean1 - mean2)

        scale = sigma if (sigma is not None and sigma > 1e-6) else 1.0
        return float(raw_contrast / scale)

    def _find_best_split(
        self,
        series: np.ndarray,
        s: int,
        e: int,
        sigma: float,
        min_len: int = 5,
    ) -> tuple[int, float]:
        """
        Finds split point t in [s + min_len, e - min_len] that maximizes studentized CUSUM contrast.
        """
        best_t = -1
        max_contrast = -1.0

        for t in range(s + min_len, e - min_len + 1):
            contrast = self.compute_cusum_contrast(series, s, t, e, sigma=sigma)
            if contrast > max_contrast:
                max_contrast = contrast
                best_t = t

        return best_t, max_contrast

    def detect_change_points_not(
        self,
        series: np.ndarray | list[float],
        threshold: float = 2.0,
        min_segment_len: int = 5,
        max_intervals: int = 250,
    ) -> list[int]:
        """
        Narrowest-Over-Thresholding (NOT) algorithm:
        1. Estimates noise scale sigma robustly via MAD.
        2. Computes the canonical asymptotic threshold tau = threshold * sqrt(2 * log(N))
           per Baranowski, Chen, Fryzlewicz (2019).
        3. Evaluates studentized contrast across multiple candidate sub-intervals.
        4. Identifies all sub-intervals whose peak contrast exceeds tau.
        5. Selects the *narrowest* interval (smallest e - s) exceeding tau.
        6. Pinpoints the change point at argmax contrast inside that narrowest interval.
        7. Recurses on disjoint left and right segments.
        """
        arr = np.asarray(series, dtype=np.float64)
        n = len(arr)
        if n < 2 * min_segment_len:
            return []

        sigma = self.estimate_noise_sigma(arr)
        # Canonical NOT critical threshold scaling
        tau = threshold * np.sqrt(2.0 * np.log(max(n, 2)))

        def not_recursive(left: int, right: int) -> list[int]:
            seg_len = right - left
            if seg_len < 2 * min_segment_len:
                return []

            # Generate candidate sub-intervals within [left, right]
            candidate_intervals: list[tuple[int, int]] = []
            lengths = [seg_len]
            curr_len = seg_len
            while curr_len >= 2 * min_segment_len:
                lengths.append(curr_len)
                curr_len = curr_len // 2

            for l_sub in set(lengths):
                if l_sub < 2 * min_segment_len:
                    continue
                step = max(1, l_sub // 4)
                for s in range(left, right - l_sub + 1, step):
                    e = s + l_sub
                    candidate_intervals.append((s, e))

            # Always include the full segment
            candidate_intervals.append((left, right))

            # Find all intervals exceeding threshold
            valid_intervals: list[
                tuple[int, int, int, float]
            ] = []  # (length, s, best_t, max_contrast)

            for s, e in candidate_intervals:
                best_t, max_c = self._find_best_split(
                    arr, s, e, sigma=sigma, min_len=min_segment_len
                )
                if max_c > tau and best_t != -1:
                    valid_intervals.append((e - s, s, best_t, max_c))

            if not valid_intervals:
                return []

            # Narrowest-Over-Threshold: choose the interval with minimal length
            # Break ties by largest contrast
            valid_intervals.sort(key=lambda x: (x[0], -x[3]))
            _, _, cp, _ = valid_intervals[0]

            # Recurse on left and right regions
            left_cps = not_recursive(left, cp)
            right_cps = not_recursive(cp, right)

            return left_cps + [cp] + right_cps

        raw_cps = not_recursive(0, n)
        # Deduplicate and sort
        unique_cps = sorted(set(raw_cps))
        return unique_cps

    def segment_series(
        self,
        series: np.ndarray | list[float],
        change_points: list[int] | None = None,
        threshold: float = 2.0,
        ai_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Partitions series into homogeneous segments separated by change-points.
        """
        arr = np.asarray(series, dtype=np.float64)
        n = len(arr)
        thresh = ai_threshold if ai_threshold is not None else self.default_ai_threshold

        if change_points is None:
            change_points = self.detect_change_points_not(arr, threshold=threshold)

        boundaries = [0] + sorted(change_points) + [n]
        # Remove consecutive duplicate boundaries
        dedup_boundaries = [boundaries[0]]
        for b in boundaries[1:]:
            if b != dedup_boundaries[-1]:
                dedup_boundaries.append(b)

        segments = []
        for i in range(len(dedup_boundaries) - 1):
            start_i = dedup_boundaries[i]
            end_i = dedup_boundaries[i + 1]
            seg_slice = arr[start_i:end_i]
            mean_sc = float(np.mean(seg_slice)) if len(seg_slice) > 0 else 0.0

            segments.append(
                {
                    "segment_index": i,
                    "start_idx": start_i,
                    "end_idx": end_i,
                    "mean_score": round(mean_sc, 4),
                    "is_ai": bool(mean_sc < thresh),
                    "length": end_i - start_i,
                }
            )

        return segments

    def map_to_paragraphs(
        self,
        document_text: str,
        intervals: list[tuple[int, int, float, bool]] | list[dict[str, Any]],
        ai_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Maps per-window score intervals to document paragraph character offsets.
        Enables accurate paragraph-level risk heatmap rendering.

        intervals: list of (start_char, end_char, score, is_ai) or dicts with corresponding keys.
        """
        thresh = ai_threshold if ai_threshold is not None else self.default_ai_threshold

        # Normalise interval list to tuples
        norm_intervals: list[tuple[int, int, float, bool]] = []
        for item in intervals:
            if isinstance(item, tuple):
                norm_intervals.append(item)
            elif isinstance(item, dict):
                norm_intervals.append(
                    (
                        int(item["start_char"]),
                        int(item["end_char"]),
                        float(item["score"]),
                        bool(item["is_ai"]),
                    )
                )

        # Split document into paragraphs using regex matching non-empty paragraphs
        # preserving exact character offsets
        paragraphs_meta: list[tuple[int, int, str]] = []
        for match in re.finditer(r"[^\n]+(?:\n[^\n]+)*", document_text):
            p_text = match.group(0).strip()
            if p_text:
                paragraphs_meta.append((match.start(), match.end(), p_text))

        mapped_results: list[dict[str, Any]] = []

        for p_idx, (p_start, p_end, p_text) in enumerate(paragraphs_meta):
            overlapping_scores: list[float] = []
            overlapping_weights: list[int] = []

            for w_start, w_end, w_score, _ in norm_intervals:
                # Calculate intersection between paragraph and window
                inter_start = max(p_start, w_start)
                inter_end = min(p_end, w_end)
                inter_len = inter_end - inter_start

                if inter_len > 0:
                    overlapping_scores.append(w_score)
                    overlapping_weights.append(inter_len)

            if overlapping_scores:
                total_weight = sum(overlapping_weights)
                weighted_score = (
                    sum(s * w for s, w in zip(overlapping_scores, overlapping_weights))
                    / total_weight
                )
            else:
                # Default to neutral human if no overlapping windows
                weighted_score = 0.9500

            is_ai = bool(weighted_score < thresh)

            mapped_results.append(
                {
                    "paragraph_idx": p_idx,
                    "start_char": p_start,
                    "end_char": p_end,
                    "text": p_text,
                    "score": round(weighted_score, 4),
                    "is_ai": is_ai,
                    "risk_tier": "ELEVATED" if is_ai else "CLEARED",
                }
            )

        return mapped_results

    def extract_interval_tuples(
        self,
        mapped_paragraphs: list[dict[str, Any]],
    ) -> list[tuple[int, int, float, bool]]:
        """
        Converts mapped paragraph records into standard [(start, end, score, is_ai)] tuples.
        """
        return [
            (
                int(p["start_char"]),
                int(p["end_char"]),
                float(p["score"]),
                bool(p["is_ai"]),
            )
            for p in mapped_paragraphs
        ]
