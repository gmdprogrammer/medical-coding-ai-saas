"""
PHI-leakage evaluation
━━━━━━━━━━━━━━━━━━━━━━
Feeds a labeled PHI test set through the three-layer anonymizer and counts
how many gold PHI spans still appear verbatim in the anonymized output.

Metrics:
  • total_phi, leaked
  • leakage_rate  = leaked / total_phi
  • recall        = 1 - leakage_rate   (higher is better — PHI successfully removed)

Usage:
  python -m eval.run_phi_eval \
      --gold eval/datasets/phi_test_set.jsonl \
      --out  eval/results/phi.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from loguru import logger  # noqa: E402

from eval.datasets.loader import iter_phi_examples  # noqa: E402
from eval.metrics import phi_leakage_rate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", required=True)
    parser.add_argument("--out", default="eval/results/phi.json")
    args = parser.parse_args()

    from app.core.phi_anonymizer import get_anonymizer  # noqa: E402

    anonymizer = get_anonymizer()

    originals: list[str] = []
    anonymized: list[str] = []
    spans: list[list[str]] = []
    rows: list[dict] = []

    for ex in iter_phi_examples(args.gold):
        result = anonymizer.anonymize(ex["text"])
        originals.append(ex["text"])
        anonymized.append(result.anonymized_text)
        spans.append(ex["phi_spans"])

        leaked_here = [s for s in ex["phi_spans"] if s and s in result.anonymized_text]
        rows.append({
            "id": ex["id"],
            "total_phi": len(ex["phi_spans"]),
            "leaked": len(leaked_here),
            "leaked_spans": leaked_here,
            "entities_removed": result.entities_removed,
            "anonymized_preview": result.anonymized_text[:300],
        })

    summary = {
        "n_examples": len(rows),
        **phi_leakage_rate(originals, anonymized, spans),
        "per_example": rows,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))

    logger.info(f"\n=== PHI Leakage Evaluation ({len(rows)} documents) ===")
    logger.info(f"Total PHI spans : {summary['total_phi']}")
    logger.info(f"Leaked          : {summary['leaked']}")
    logger.info(f"Leakage rate    : {summary['leakage_rate']:.3f}")
    logger.info(f"Recall          : {summary['recall']:.3f}")
    logger.info(f"Results         → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
