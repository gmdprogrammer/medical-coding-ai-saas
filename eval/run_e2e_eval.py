"""
End-to-end coding evaluation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Streams each clinical note through the full RAG pipeline
(anonymize → FAISS retrieve → Groq LLM → structured JSON),
then scores the returned ICD-10 / CPT code sets against gold.

Metrics: micro-PRF, macro-PRF, per-chapter micro-F1, mean latency.

Cost warning
  Each example costs one Groq API call. 20 examples ≈ free tier friendly.
  For 1,000+ documents, provision a paid tier and cache responses.

Usage:
  export GROQ_API_KEY=...
  python -m eval.run_e2e_eval \
      --gold eval/datasets/starter_gold.jsonl \
      --out  eval/results/e2e.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from loguru import logger  # noqa: E402

from eval.datasets.loader import iter_coding_examples  # noqa: E402
from eval.metrics import macro_prf, micro_prf, per_chapter_f1  # noqa: E402


async def run(gold_path: str, out_path: str, max_examples: int | None) -> int:
    from app.services.rag_service import get_rag_pipeline  # noqa: E402
    from app.services.vector_store import get_vector_store  # noqa: E402

    store = get_vector_store()
    if store.total_documents == 0:
        logger.error("FAISS index is empty. Build it before running e2e eval.")
        return 2

    pipeline = get_rag_pipeline()

    icd_pairs: list[tuple[set[str], set[str]]] = []
    cpt_pairs: list[tuple[set[str], set[str]]] = []
    rows: list[dict] = []
    latencies: list[int] = []
    failures: list[dict] = []

    examples = list(iter_coding_examples(gold_path))
    if max_examples:
        examples = examples[:max_examples]
    logger.info(f"Evaluating {len(examples)} examples...")

    for ex in examples:
        session_id = f"eval_{uuid.uuid4().hex[:8]}"
        t0 = time.perf_counter()
        try:
            result = await pipeline.process(
                clinical_text=ex["text"],
                session_id=session_id,
                top_k=5,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[{ex['id']}] pipeline failed: {exc}")
            failures.append({"id": ex["id"], "error": str(exc)[:300]})
            continue

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        latencies.append(elapsed_ms)

        pred_icd = {c.code for c in result["icd10_codes"] if c.code}
        pred_cpt = {c.code for c in result["cpt_codes"] if c.code}

        icd_pairs.append((ex["gold_icd10"], pred_icd))
        if ex["gold_cpt"]:
            cpt_pairs.append((ex["gold_cpt"], pred_cpt))

        rows.append({
            "id": ex["id"],
            "gold_icd10": sorted(ex["gold_icd10"]),
            "pred_icd10": sorted(pred_icd),
            "gold_cpt": sorted(ex["gold_cpt"]),
            "pred_cpt": sorted(pred_cpt),
            "latency_ms": elapsed_ms,
            "phi_removed": result["entities_removed"],
        })

    summary = {
        "n_examples": len(rows),
        "n_failures": len(failures),
        "latency_ms": {
            "mean": int(sum(latencies) / len(latencies)) if latencies else 0,
            "p50": sorted(latencies)[len(latencies) // 2] if latencies else 0,
            "p95": sorted(latencies)[int(len(latencies) * 0.95) - 1] if len(latencies) > 1 else 0,
        },
        "icd10": {
            "micro": micro_prf(icd_pairs),
            "macro": macro_prf(icd_pairs),
            "per_chapter": per_chapter_f1(icd_pairs),
        },
        "cpt": {
            "micro": micro_prf(cpt_pairs),
            "macro": macro_prf(cpt_pairs),
        } if cpt_pairs else None,
        "failures": failures,
        "per_example": rows,
    }

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, default=str))

    logger.info(f"\n=== End-to-End Evaluation ({len(rows)} examples) ===")
    m = summary["icd10"]["micro"]
    logger.info(f"ICD-10 micro  P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f}")
    m = summary["icd10"]["macro"]
    logger.info(f"ICD-10 macro  P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f}")
    if summary["cpt"]:
        m = summary["cpt"]["micro"]
        logger.info(f"CPT micro     P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f}")
    logger.info(f"Latency mean  {summary['latency_ms']['mean']} ms  "
                f"(p95 {summary['latency_ms']['p95']} ms)")
    logger.info(f"Results       → {out}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", required=True)
    parser.add_argument("--out", default="eval/results/e2e.json")
    parser.add_argument("--max-examples", type=int, default=None)
    args = parser.parse_args()
    return asyncio.run(run(args.gold, args.out, args.max_examples))


if __name__ == "__main__":
    raise SystemExit(main())
