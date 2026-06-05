"""
Reproducible end-to-end evaluation run
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Executes retrieval, PHI, and end-to-end scoring in sequence and writes a
LaTeX-ready summary table to eval/results/report.md.

Usage (from repo root):
    python -m eval.run_all --gold eval/datasets/starter_gold.jsonl \
                           --phi  eval/datasets/phi_test_set.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(module: str, args: list[str]) -> int:
    cmd = [sys.executable, "-m", module, *args]
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=ROOT)


def _render_report(results_dir: Path) -> str:
    def _read(name: str) -> dict | None:
        p = results_dir / name
        return json.loads(p.read_text()) if p.exists() else None

    retr = _read("retrieval.json")
    e2e = _read("e2e.json")
    phi = _read("phi.json")

    lines = ["# Evaluation Report", ""]

    if retr:
        r = retr["recall_at_k"]
        lines += [
            "## Retrieval (ICD-10 FAISS shortlist)",
            "",
            f"- Examples: **{retr['n_examples']}**  |  Index size: **{retr['index_size']:,}**",
            f"- Throughput: **{retr['queries_per_second']} q/s**",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Recall@1  | {r['1']:.3f} |",
            f"| Recall@5  | {r['5']:.3f} |",
            f"| Recall@10 | {r['10']:.3f} |",
            f"| Recall@20 | {r['20']:.3f} |",
            f"| MRR       | {retr['mrr']:.3f} |",
            "",
        ]

    if e2e:
        mi = e2e["icd10"]["micro"]
        ma = e2e["icd10"]["macro"]
        lines += [
            "## End-to-End Coding Accuracy",
            "",
            f"- Examples: **{e2e['n_examples']}**  |  Failures: {e2e['n_failures']}",
            f"- Latency: mean **{e2e['latency_ms']['mean']} ms**, p95 {e2e['latency_ms']['p95']} ms",
            "",
            "| Metric | Precision | Recall | F1 |",
            "|---|---|---|---|",
            f"| ICD-10 micro | {mi['precision']:.3f} | {mi['recall']:.3f} | **{mi['f1']:.3f}** |",
            f"| ICD-10 macro | {ma['precision']:.3f} | {ma['recall']:.3f} | **{ma['f1']:.3f}** |",
        ]
        if e2e.get("cpt"):
            cm = e2e["cpt"]["micro"]
            lines.append(
                f"| CPT micro    | {cm['precision']:.3f} | {cm['recall']:.3f} | **{cm['f1']:.3f}** |"
            )
        lines.append("")

    if phi:
        lines += [
            "## PHI Leakage",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Documents     | {phi['n_examples']} |",
            f"| Total PHI     | {phi['total_phi']} |",
            f"| Leaked        | {phi['leaked']} |",
            f"| Leakage rate  | {phi['leakage_rate']:.3f} |",
            f"| PHI recall    | **{phi['recall']:.3f}** |",
            "",
        ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", default="eval/datasets/starter_gold.jsonl")
    parser.add_argument("--phi", default="eval/datasets/phi_test_set.jsonl")
    parser.add_argument("--skip-e2e", action="store_true",
                        help="Skip the Groq-calling e2e stage (useful for offline smoke tests).")
    parser.add_argument("--max-examples", type=int, default=None)
    args = parser.parse_args()

    results = ROOT / "eval" / "results"
    results.mkdir(parents=True, exist_ok=True)

    rc = 0
    rc |= _run("eval.run_retrieval_eval",
               ["--gold", args.gold, "--out", str(results / "retrieval.json")])
    rc |= _run("eval.run_phi_eval",
               ["--gold", args.phi, "--out", str(results / "phi.json")])
    if not args.skip_e2e:
        e2e_args = ["--gold", args.gold, "--out", str(results / "e2e.json")]
        if args.max_examples:
            e2e_args += ["--max-examples", str(args.max_examples)]
        rc |= _run("eval.run_e2e_eval", e2e_args)

    report = _render_report(results)
    (results / "report.md").write_text(report)
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)
    print(f"\nReport written to {results / 'report.md'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
