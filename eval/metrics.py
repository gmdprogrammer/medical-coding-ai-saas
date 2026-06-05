"""
Evaluation Metrics
━━━━━━━━━━━━━━━━━━
Implements the standard information-retrieval and multi-label classification
metrics used in medical-coding literature.

Reference metrics (Johnson et al., 2023; Mullenbach et al., 2018; CodiEsp 2020):
  • Recall@k, Precision@k            — retrieval quality of FAISS shortlist
  • Mean Reciprocal Rank (MRR)       — average rank of first gold hit
  • Micro / Macro Precision-Recall-F1 — end-to-end coding accuracy
  • Per-chapter F1                    — long-tail analysis

All functions operate on python sets/lists — no framework dependency.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Iterable, Sequence


# ── Retrieval metrics ────────────────────────────────────────────────────────

def recall_at_k(gold: set[str], predicted_ranked: Sequence[str], k: int) -> float:
    if not gold:
        return 0.0
    topk = set(predicted_ranked[:k])
    return len(gold & topk) / len(gold)


def precision_at_k(gold: set[str], predicted_ranked: Sequence[str], k: int) -> float:
    if k == 0 or not predicted_ranked:
        return 0.0
    topk = predicted_ranked[:k]
    if not topk:
        return 0.0
    return sum(1 for c in topk if c in gold) / len(topk)


def reciprocal_rank(gold: set[str], predicted_ranked: Sequence[str]) -> float:
    for i, code in enumerate(predicted_ranked, start=1):
        if code in gold:
            return 1.0 / i
    return 0.0


def mean_reciprocal_rank(results: Iterable[tuple[set[str], Sequence[str]]]) -> float:
    rrs = [reciprocal_rank(g, p) for g, p in results]
    return mean(rrs) if rrs else 0.0


# ── Classification metrics (multi-label) ─────────────────────────────────────

def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def micro_prf(
    per_example: Iterable[tuple[set[str], set[str]]],
) -> dict[str, float]:
    """Aggregate TP/FP/FN across all examples, then compute P/R/F."""
    tp = fp = fn = 0
    for gold, pred in per_example:
        tp += len(gold & pred)
        fp += len(pred - gold)
        fn += len(gold - pred)
    p, r, f = _prf(tp, fp, fn)
    return {"precision": p, "recall": r, "f1": f, "tp": tp, "fp": fp, "fn": fn}


def macro_prf(
    per_example: Iterable[tuple[set[str], set[str]]],
) -> dict[str, float]:
    """
    Per-code P/R/F averaged uniformly.
    Computed by aggregating TP/FP/FN per distinct code across the corpus.
    """
    per_code: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for gold, pred in per_example:
        for c in gold & pred:
            per_code[c]["tp"] += 1
        for c in pred - gold:
            per_code[c]["fp"] += 1
        for c in gold - pred:
            per_code[c]["fn"] += 1

    if not per_code:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "n_codes": 0}

    ps, rs, fs = [], [], []
    for counts in per_code.values():
        p, r, f = _prf(counts["tp"], counts["fp"], counts["fn"])
        ps.append(p)
        rs.append(r)
        fs.append(f)

    return {
        "precision": mean(ps),
        "recall": mean(rs),
        "f1": mean(fs),
        "n_codes": len(per_code),
    }


def per_chapter_f1(
    per_example: Iterable[tuple[set[str], set[str]]],
) -> dict[str, dict[str, float]]:
    """
    Group by ICD-10 chapter (first character of the code, e.g. 'E' in E11.9).
    Useful for exposing long-tail behaviour.
    """
    buckets: dict[str, list[tuple[set[str], set[str]]]] = defaultdict(list)
    for gold, pred in per_example:
        codes = gold | pred
        for prefix in {c[0] for c in codes if c}:
            g_sub = {c for c in gold if c and c[0] == prefix}
            p_sub = {c for c in pred if c and c[0] == prefix}
            buckets[prefix].append((g_sub, p_sub))

    return {chapter: micro_prf(pairs) for chapter, pairs in sorted(buckets.items())}


# ── PHI-leakage metrics ──────────────────────────────────────────────────────

def phi_leakage_rate(
    originals: list[str],
    anonymized: list[str],
    gold_phi_spans: list[list[str]],
) -> dict[str, float]:
    """
    For each document, count how many gold PHI spans still appear verbatim
    in the anonymized output.
      leakage_rate = leaked_spans / total_gold_spans
      recall       = 1 - leakage_rate   (PHI successfully removed)
    """
    total = leaked = 0
    for anon_text, spans in zip(anonymized, gold_phi_spans):
        for span in spans:
            total += 1
            if span and span in anon_text:
                leaked += 1
    if total == 0:
        return {"total_phi": 0, "leaked": 0, "leakage_rate": 0.0, "recall": 1.0}
    return {
        "total_phi": total,
        "leaked": leaked,
        "leakage_rate": leaked / total,
        "recall": 1.0 - leaked / total,
    }
