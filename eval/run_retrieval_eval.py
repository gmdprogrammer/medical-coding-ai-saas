"""
Retrieval-only evaluation
━━━━━━━━━━━━━━━━━━━━━━━━━
Measures how well the FAISS index surfaces the gold ICD-10 code inside
its top-k shortlist. This is *upper-bound* analysis for the full pipeline:
if the retriever misses a code, the LLM cannot recover it.

Metrics:
  • Recall@1, Recall@5, Recall@10, Recall@20
  • Precision@1, Precision@5
  • Mean Reciprocal Rank (MRR)

Runs entirely offline — no Groq API calls, no PHI anonymization.
Usage:
  python -m eval.run_retrieval_eval \
      --gold eval/datasets/starter_gold.jsonl \
      --out  eval/results/retrieval.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Make the backend package importable when run from repo root.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from loguru import logger  # noqa: E402

from eval.datasets.loader import iter_coding_examples  # noqa: E402
from eval.metrics import (  # noqa: E402
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", required=True, help="Path to gold JSONL")
    parser.add_argument("--out", default="eval/results/retrieval.json")
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()

    from app.services.vector_store import get_vector_store  # noqa: E402

    store = get_vector_store()
    if store.total_documents == 0:
        logger.error(
            "FAISS index is empty. Build it first:\n"
            "  python data_pipeline/scripts/preprocess.py\n"
            "  python data_pipeline/scripts/build_index.py --input <jsonl> --output data/vector_stores/faiss_index"
        )
        return 2

    logger.info(f"Index loaded: {store.total_documents} docs "
                f"(ICD={store.icd10_count}, CPT/HCPCS={store.cpt_count})")

    per_example_rr = []
    per_k: dict[int, list[float]] = {k: [] for k in (1, 5, 10, 20)}
    prec_per_k: dict[int, list[float]] = {k: [] for k in (1, 5)}
    rows = []

    t0 = time.perf_counter()
    for ex in iter_coding_examples(args.gold):
        gold = ex["gold_icd10"]
        if not gold:
            continue

        hits = store.search_icd10(ex["text"], top_k=args.top_k)
        ranked = [h["code"] for h in hits]

        for k in per_k:
            per_k[k].append(recall_at_k(gold, ranked, k))
        for k in prec_per_k:
            prec_per_k[k].append(precision_at_k(gold, ranked, k))
        per_example_rr.append((gold, ranked))

        rows.append({
            "id": ex["id"],
            "gold": sorted(gold),
            "top5": ranked[:5],
            "hit_rank": next((i + 1 for i, c in enumerate(ranked) if c in gold), None),
        })

    elapsed = time.perf_counter() - t0
    n = len(rows)

    summary = {
        "n_examples": n,
        "index_size": store.total_documents,
        "elapsed_seconds": round(elapsed, 2),
        "queries_per_second": round(n / elapsed, 2) if elapsed > 0 else 0.0,
        "recall_at_k": {
            str(k): round(sum(v) / len(v), 4) if v else 0.0 for k, v in per_k.items()
        },
        "precision_at_k": {
            str(k): round(sum(v) / len(v), 4) if v else 0.0 for k, v in prec_per_k.items()
        },
        "mrr": round(mean_reciprocal_rank(per_example_rr), 4),
        "per_example": rows,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2))

    logger.info(f"\n=== Retrieval Evaluation ({n} examples) ===")
    logger.info(f"Recall@1  = {summary['recall_at_k']['1']:.3f}")
    logger.info(f"Recall@5  = {summary['recall_at_k']['5']:.3f}")
    logger.info(f"Recall@10 = {summary['recall_at_k']['10']:.3f}")
    logger.info(f"Recall@20 = {summary['recall_at_k']['20']:.3f}")
    logger.info(f"MRR       = {summary['mrr']:.3f}")
    logger.info(f"Results  → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
