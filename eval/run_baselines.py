"""
Baseline comparison runner
━━━━━━━━━━━━━━━━━━━━━━━━━━
Runs each baseline retriever against the same gold set and reports
Recall@k, Precision@k, MRR, and queries/sec. Writes a Markdown
comparison table ready for §4.9 of the paper.

Baselines included:
  • bm25      — Okapi BM25 (rank_bm25)
  • dense     — sentence-transformers/all-MiniLM-L6-v2 + FAISS IndexFlatIP
  • hybrid    — Reciprocal Rank Fusion of bm25 + dense (k=60)

Optional (if PubMedBERT weights are available):
  • biobert   — pritamdeka/S-PubMedBert-MS-MARCO + FAISS

Usage
  python -m eval.run_baselines \
      --gold   eval/datasets/starter_gold.jsonl \
      --corpus data/processed/medical_codes_v2024.jsonl \
      --out    eval/results/baselines.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from loguru import logger  # noqa: E402

from eval.datasets.loader import iter_coding_examples  # noqa: E402
from eval.metrics import (  # noqa: E402
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)


def _score_retriever(name: str, retriever, examples: list[dict], top_k: int) -> dict:
    rec_k = {1: [], 5: [], 10: [], 20: []}
    prc_k = {1: [], 5: []}
    mrr_pairs: list[tuple[set[str], list[str]]] = []
    failures = 0

    t0 = time.perf_counter()
    for ex in examples:
        gold = ex["gold_icd10"]
        if not gold:
            continue
        try:
            hits = retriever.search_icd10(ex["text"], top_k=top_k)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[{name}/{ex['id']}] failed: {exc}")
            failures += 1
            continue
        ranked = [h["code"] for h in hits]
        for k in rec_k:
            rec_k[k].append(recall_at_k(gold, ranked, k))
        for k in prc_k:
            prc_k[k].append(precision_at_k(gold, ranked, k))
        mrr_pairs.append((gold, ranked))
    elapsed = time.perf_counter() - t0
    n = len(mrr_pairs)
    return {
        "name": name,
        "n": n,
        "failures": failures,
        "elapsed_s": round(elapsed, 2),
        "qps": round(n / elapsed, 2) if elapsed > 0 else 0.0,
        "recall_at_k": {str(k): round(sum(v) / len(v), 4) if v else 0.0 for k, v in rec_k.items()},
        "precision_at_k": {str(k): round(sum(v) / len(v), 4) if v else 0.0 for k, v in prc_k.items()},
        "mrr": round(mean_reciprocal_rank(mrr_pairs), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", required=True)
    parser.add_argument("--corpus", required=True,
                        help="Path to the cleaned JSONL produced by preprocess.py "
                             "(used for BM25/Hybrid; dense uses the prebuilt FAISS index).")
    parser.add_argument("--out", default="eval/results/baselines.json")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--include", default="bm25,dense,hybrid",
                        help="Comma-separated subset of: bm25, dense, hybrid")
    args = parser.parse_args()

    include = {x.strip() for x in args.include.split(",") if x.strip()}
    examples = list(iter_coding_examples(args.gold))
    logger.info(f"Evaluating {len(examples)} gold examples on {sorted(include)}")

    summaries: list[dict] = []
    sparse = dense = None

    if "bm25" in include or "hybrid" in include:
        from eval.baselines.bm25_retriever import BM25Retriever
        sparse = BM25Retriever()
        sparse.load_corpus(args.corpus)
        if "bm25" in include:
            summaries.append(_score_retriever("BM25 (Okapi)", sparse, examples, args.top_k))

    if "dense" in include or "hybrid" in include:
        from app.services.vector_store import get_vector_store
        dense = get_vector_store()
        if dense.total_documents == 0:
            logger.error("FAISS index empty — build it before running dense/hybrid baselines.")
            return 2
        if "dense" in include:
            summaries.append(_score_retriever("Dense (MiniLM-L6-v2 + FAISS)", dense, examples, args.top_k))

    if "hybrid" in include and sparse and dense:
        from eval.baselines.hybrid_rrf import HybridRRFRetriever
        hybrid = HybridRRFRetriever(dense=dense, sparse=sparse, k=60)
        summaries.append(_score_retriever("Hybrid RRF (k=60)", hybrid, examples, args.top_k))

    md = _render_markdown(summaries)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summaries, indent=2))
    md_path = out.with_suffix(".md")
    md_path.write_text(md)
    logger.info(f"\n{md}\nResults → {out}\nReport  → {md_path}")
    return 0


def _render_markdown(summaries: list[dict]) -> str:
    if not summaries:
        return "_No baselines produced output._"
    lines = [
        "## Baseline Comparison — ICD-10 Retrieval",
        "",
        f"_N = {summaries[0]['n']}; gold set = `eval/datasets/starter_gold.jsonl` (synthetic pilot)._",
        "",
        "| Retriever | R@1 | R@5 | R@10 | R@20 | P@1 | P@5 | MRR | q/s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        r = s["recall_at_k"]
        p = s["precision_at_k"]
        lines.append(
            f"| {s['name']} | "
            f"{r['1']:.3f} | {r['5']:.3f} | {r['10']:.3f} | {r['20']:.3f} | "
            f"{p['1']:.3f} | {p['5']:.3f} | "
            f"{s['mrr']:.3f} | {s['qps']:.1f} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
