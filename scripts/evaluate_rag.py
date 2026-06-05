"""
RAG Accuracy Evaluation Script
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Measures three layers of accuracy:

  1. Retrieval Recall@K  — are the gold codes present in the FAISS top-K results?
  2. End-to-End Precision / Recall / F1  — do the LLM-returned codes match gold?
  3. Confidence Calibration  — does high confidence actually mean correct?

Run from the project root (with backend venv active):

  cd backend
  source .venv/bin/activate          # Windows: .venv\Scripts\activate
  cd ..
  python scripts/evaluate_rag.py

Optional flags:
  --dataset   path to a custom JSONL eval file (see format below)
  --top-k     number of codes to request from the pipeline  (default: 5)
  --retrieval-k  FAISS candidates to check recall against   (default: 10)
  --no-llm    skip the Groq LLM step (retrieval-only eval, free + fast)
  --output    path to write a JSON results file

Custom JSONL format (one JSON object per line):
  {
    "note": "Patient presents with uncontrolled type 2 diabetes...",
    "icd10": ["E11.9", "E11.65"],
    "cpt":   ["99213", "80053"]
  }
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# ── Make sure the backend package is importable ───────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)  # so relative paths in config (.env, faiss index) resolve

# ── Built-in labeled test set ─────────────────────────────────────────────────
# 15 realistic clinical vignettes with gold-standard codes.
# Extend this list or supply --dataset to use your own.
BUILTIN_DATASET: list[dict] = [
    {
        "note": (
            "58-year-old male with a 10-year history of type 2 diabetes mellitus. "
            "HbA1c 9.2%, fasting glucose 210 mg/dL. No current insulin use. "
            "Referred for diabetes education and medication adjustment."
        ),
        "icd10": ["E11.9"],
        "cpt": ["99213"],
    },
    {
        "note": (
            "Patient with essential hypertension, blood pressure 158/96 mmHg. "
            "Currently on lisinopril 10 mg daily. Advised lifestyle modification."
        ),
        "icd10": ["I10"],
        "cpt": ["99213"],
    },
    {
        "note": (
            "65-year-old female admitted with community-acquired pneumonia. "
            "Chest X-ray shows right lower lobe consolidation. "
            "Started on IV antibiotics. Two-view chest radiograph obtained."
        ),
        "icd10": ["J18.9"],
        "cpt": ["71046"],
    },
    {
        "note": (
            "Patient with stage 3 chronic kidney disease. eGFR 42 mL/min. "
            "Serum creatinine 1.9 mg/dL. Referred to nephrology for management."
        ),
        "icd10": ["N18.3"],
        "cpt": ["99213"],
    },
    {
        "note": (
            "Routine lipid panel shows total cholesterol 268 mg/dL, LDL 182 mg/dL. "
            "Diagnosis of hyperlipidemia. Initiated statin therapy."
        ),
        "icd10": ["E78.5"],
        "cpt": ["80061"],
    },
    {
        "note": (
            "Patient presents with acute ST-elevation myocardial infarction of the "
            "anterior wall. Emergent cardiac catheterization performed. "
            "12-lead ECG confirms STEMI."
        ),
        "icd10": ["I21.09"],
        "cpt": ["93000"],
    },
    {
        "note": (
            "45-year-old with major depressive disorder, recurrent, moderate severity. "
            "PHQ-9 score 14. Initiated sertraline 50 mg. Follow-up in 4 weeks."
        ),
        "icd10": ["F33.1"],
        "cpt": ["99213"],
    },
    {
        "note": (
            "Patient with asthma, mild persistent. FEV1 78% predicted. "
            "Prescribed inhaled corticosteroid. Spirometry performed."
        ),
        "icd10": ["J45.30"],
        "cpt": ["94010"],
    },
    {
        "note": (
            "Comprehensive metabolic panel ordered for annual wellness visit. "
            "Results within normal limits. Patient is a 40-year-old established patient."
        ),
        "icd10": ["Z00.00"],
        "cpt": ["80053"],
    },
    {
        "note": (
            "Patient with iron deficiency anemia. Hemoglobin 9.1 g/dL, ferritin 6 ng/mL. "
            "CBC with differential obtained. Oral iron supplementation started."
        ),
        "icd10": ["D50.9"],
        "cpt": ["85025"],
    },
    {
        "note": (
            "Type 2 diabetic patient with diabetic chronic kidney disease stage 3. "
            "HbA1c 8.4%, eGFR 38. Adjusted metformin dose. "
            "Comprehensive metabolic panel and HbA1c ordered."
        ),
        "icd10": ["E11.65", "N18.3"],
        "cpt": ["80053"],
    },
    {
        "note": (
            "Patient with congestive heart failure, systolic, chronic. "
            "Ejection fraction 35%. BNP elevated at 820 pg/mL. "
            "Echocardiogram performed. Furosemide dose increased."
        ),
        "icd10": ["I50.20"],
        "cpt": ["93306"],
    },
    {
        "note": (
            "Acute upper respiratory infection. Rhinorrhea, sore throat, low-grade fever. "
            "No bacterial signs. Symptomatic treatment recommended."
        ),
        "icd10": ["J06.9"],
        "cpt": ["99213"],
    },
    {
        "note": (
            "Patient with hypothyroidism on levothyroxine. TSH 6.8 mIU/L. "
            "Dose adjusted. Thyroid function tests ordered."
        ),
        "icd10": ["E03.9"],
        "cpt": ["84443"],
    },
    {
        "note": (
            "Established patient with obesity, BMI 38.2. Counseled on diet and exercise. "
            "Referred to weight management program. Blood pressure 142/88."
        ),
        "icd10": ["E66.9", "I10"],
        "cpt": ["99213"],
    },
]


# ── Metrics helpers ───────────────────────────────────────────────────────────

def _normalise(code: str) -> str:
    """Strip dots and uppercase for loose matching (E11.9 == E119)."""
    return code.upper().replace(".", "").strip()


def _codes_match(predicted: str, gold: str) -> bool:
    return _normalise(predicted) == _normalise(gold)


def retrieval_recall_at_k(
    retrieved: list[dict],
    gold_codes: list[str],
) -> float:
    """Fraction of gold codes found anywhere in the retrieved list."""
    if not gold_codes:
        return 1.0
    retrieved_normalised = {_normalise(r["code"]) for r in retrieved}
    hits = sum(1 for g in gold_codes if _normalise(g) in retrieved_normalised)
    return hits / len(gold_codes)


def precision_recall_f1(
    predicted_codes: list[str],
    gold_codes: list[str],
) -> tuple[float, float, float]:
    """Exact-match precision, recall, F1 for a single sample."""
    if not predicted_codes and not gold_codes:
        return 1.0, 1.0, 1.0
    if not predicted_codes:
        return 0.0, 0.0, 0.0
    if not gold_codes:
        return 0.0, 1.0, 0.0  # predicted something when nothing expected

    pred_norm = [_normalise(c) for c in predicted_codes]
    gold_norm = [_normalise(c) for c in gold_codes]

    tp = sum(1 for p in pred_norm if p in gold_norm)
    precision = tp / len(pred_norm)
    recall = tp / len(gold_norm)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


# ── Retrieval-only evaluation (no LLM call) ───────────────────────────────────

def evaluate_retrieval(
    dataset: list[dict],
    retrieval_k: int,
) -> dict[str, Any]:
    """
    Checks whether gold codes appear in the FAISS top-K results.
    Does NOT call the Groq API — fast and free.
    """
    from app.services.vector_store import get_vector_store

    print("\n── Initialising vector store ──")
    vs = get_vector_store()
    print(f"   Index size: {vs.total_documents} documents "
          f"({vs.icd10_count} ICD-10, {vs.cpt_count} CPT/HCPCS)\n")

    icd_recalls, cpt_recalls = [], []
    per_sample = []

    for i, sample in enumerate(dataset, 1):
        note = sample["note"]
        gold_icd = sample.get("icd10", [])
        gold_cpt = sample.get("cpt", [])

        icd_results = vs.search_icd10(note, top_k=retrieval_k)
        cpt_results = vs.search_cpt(note, top_k=retrieval_k)

        icd_recall = retrieval_recall_at_k(icd_results, gold_icd)
        cpt_recall = retrieval_recall_at_k(cpt_results, gold_cpt)

        icd_recalls.append(icd_recall)
        cpt_recalls.append(cpt_recall)

        status = "✓" if (icd_recall == 1.0 and cpt_recall == 1.0) else "✗"
        print(
            f"  [{i:02d}] {status}  ICD recall={icd_recall:.2f}  "
            f"CPT recall={cpt_recall:.2f}  "
            f"| gold_icd={gold_icd}  gold_cpt={gold_cpt}"
        )

        per_sample.append({
            "note_preview": note[:80] + "...",
            "gold_icd": gold_icd,
            "gold_cpt": gold_cpt,
            "icd_recall_at_k": icd_recall,
            "cpt_recall_at_k": cpt_recall,
            "top_icd_retrieved": [r["code"] for r in icd_results[:5]],
            "top_cpt_retrieved": [r["code"] for r in cpt_results[:5]],
        })

    mean_icd = sum(icd_recalls) / len(icd_recalls) if icd_recalls else 0.0
    mean_cpt = sum(cpt_recalls) / len(cpt_recalls) if cpt_recalls else 0.0
    overall = (mean_icd + mean_cpt) / 2

    return {
        "retrieval_k": retrieval_k,
        "n_samples": len(dataset),
        "mean_icd_recall_at_k": round(mean_icd, 4),
        "mean_cpt_recall_at_k": round(mean_cpt, 4),
        "overall_retrieval_recall": round(overall, 4),
        "per_sample": per_sample,
    }


# ── End-to-end evaluation (retrieval + LLM) ───────────────────────────────────

async def evaluate_end_to_end(
    dataset: list[dict],
    top_k: int,
    retrieval_k: int,
) -> dict[str, Any]:
    """
    Runs each note through the full RAG pipeline (FAISS + Groq LLM)
    and computes precision, recall, F1 against gold codes.
    """
    from app.services.rag_service import get_rag_pipeline

    print("\n── Initialising RAG pipeline ──")
    pipeline = get_rag_pipeline()

    icd_precisions, icd_recalls, icd_f1s = [], [], []
    cpt_precisions, cpt_recalls, cpt_f1s = [], [], []
    icd_retrieval_recalls, cpt_retrieval_recalls = [], []
    confidence_correct, confidence_wrong = [], []
    per_sample = []
    total_latency_ms = 0

    for i, sample in enumerate(dataset, 1):
        note = sample["note"]
        gold_icd = sample.get("icd10", [])
        gold_cpt = sample.get("cpt", [])

        print(f"\n  [{i:02d}/{len(dataset)}] Running pipeline...")
        t0 = time.perf_counter()

        try:
            result = await pipeline.process(
                clinical_text=note,
                session_id=f"eval-{i:03d}",
                top_k=top_k,
            )
        except Exception as exc:
            print(f"         ⚠ Pipeline error: {exc}")
            per_sample.append({"error": str(exc), "note_preview": note[:80]})
            continue

        latency = int((time.perf_counter() - t0) * 1000)
        total_latency_ms += latency

        pred_icd = [c.code for c in result["icd10_codes"]]
        pred_cpt = [c.code for c in result["cpt_codes"]]

        # Retrieval recall (from the raw vector store results embedded in pipeline)
        from app.services.vector_store import get_vector_store
        vs = get_vector_store()
        icd_retrieved = vs.search_icd10(result["anonymized_text"], top_k=retrieval_k)
        cpt_retrieved = vs.search_cpt(result["anonymized_text"], top_k=retrieval_k)
        icd_ret_recall = retrieval_recall_at_k(icd_retrieved, gold_icd)
        cpt_ret_recall = retrieval_recall_at_k(cpt_retrieved, gold_cpt)
        icd_retrieval_recalls.append(icd_ret_recall)
        cpt_retrieval_recalls.append(cpt_ret_recall)

        # End-to-end metrics
        ip, ir, if1 = precision_recall_f1(pred_icd, gold_icd)
        cp, cr, cf1 = precision_recall_f1(pred_cpt, gold_cpt)

        icd_precisions.append(ip)
        icd_recalls.append(ir)
        icd_f1s.append(if1)
        cpt_precisions.append(cp)
        cpt_recalls.append(cr)
        cpt_f1s.append(cf1)

        # Confidence calibration: collect (confidence, is_correct) pairs
        gold_icd_norm = {_normalise(g) for g in gold_icd}
        gold_cpt_norm = {_normalise(g) for g in gold_cpt}
        for c in result["icd10_codes"]:
            correct = _normalise(c.code) in gold_icd_norm
            (confidence_correct if correct else confidence_wrong).append(c.confidence)
        for c in result["cpt_codes"]:
            correct = _normalise(c.code) in gold_cpt_norm
            (confidence_correct if correct else confidence_wrong).append(c.confidence)

        status = "✓" if (if1 == 1.0 and cf1 == 1.0) else ("~" if (if1 > 0 or cf1 > 0) else "✗")
        print(
            f"         {status}  ICD  P={ip:.2f} R={ir:.2f} F1={if1:.2f}  |  "
            f"CPT  P={cp:.2f} R={cr:.2f} F1={cf1:.2f}  |  {latency}ms"
        )
        print(f"            gold_icd={gold_icd}  pred_icd={pred_icd}")
        print(f"            gold_cpt={gold_cpt}  pred_cpt={pred_cpt}")

        per_sample.append({
            "note_preview": note[:80] + "...",
            "gold_icd": gold_icd,
            "gold_cpt": gold_cpt,
            "pred_icd": pred_icd,
            "pred_cpt": pred_cpt,
            "icd_precision": round(ip, 4),
            "icd_recall": round(ir, 4),
            "icd_f1": round(if1, 4),
            "cpt_precision": round(cp, 4),
            "cpt_recall": round(cr, 4),
            "cpt_f1": round(cf1, 4),
            "icd_retrieval_recall_at_k": round(icd_ret_recall, 4),
            "cpt_retrieval_recall_at_k": round(cpt_ret_recall, 4),
            "avg_icd_confidence": result["avg_icd_confidence"],
            "avg_cpt_confidence": result["avg_cpt_confidence"],
            "latency_ms": latency,
        })

    def _avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    avg_conf_correct = _avg(confidence_correct)
    avg_conf_wrong = _avg(confidence_wrong)
    calibration_gap = round(avg_conf_correct - avg_conf_wrong, 4)

    return {
        "n_samples": len(dataset),
        "top_k": top_k,
        "retrieval_k": retrieval_k,
        # Retrieval layer
        "mean_icd_retrieval_recall_at_k": _avg(icd_retrieval_recalls),
        "mean_cpt_retrieval_recall_at_k": _avg(cpt_retrieval_recalls),
        # End-to-end ICD-10
        "icd_precision": _avg(icd_precisions),
        "icd_recall": _avg(icd_recalls),
        "icd_f1": _avg(icd_f1s),
        # End-to-end CPT
        "cpt_precision": _avg(cpt_precisions),
        "cpt_recall": _avg(cpt_recalls),
        "cpt_f1": _avg(cpt_f1s),
        # Overall
        "overall_f1": _avg(icd_f1s + cpt_f1s),
        # Confidence calibration
        "avg_confidence_when_correct": avg_conf_correct,
        "avg_confidence_when_wrong": avg_conf_wrong,
        "calibration_gap": calibration_gap,
        # Latency
        "avg_latency_ms": round(total_latency_ms / len(per_sample), 1) if per_sample else 0,
        "total_latency_ms": total_latency_ms,
        "per_sample": per_sample,
    }


# ── Report printer ────────────────────────────────────────────────────────────

def print_report(retrieval: dict, e2e: dict | None) -> None:
    sep = "═" * 60

    print(f"\n{sep}")
    print("  RAG EVALUATION REPORT")
    print(sep)

    print(f"\n{'─'*60}")
    print("  RETRIEVAL LAYER  (FAISS top-K recall)")
    print(f"{'─'*60}")
    print(f"  Retrieval K          : {retrieval['retrieval_k']}")
    print(f"  Samples              : {retrieval['n_samples']}")
    print(f"  ICD-10 Recall@K      : {retrieval['mean_icd_recall_at_k']:.1%}")
    print(f"  CPT    Recall@K      : {retrieval['mean_cpt_recall_at_k']:.1%}")
    print(f"  Overall Recall@K     : {retrieval['overall_retrieval_recall']:.1%}")

    if e2e:
        print(f"\n{'─'*60}")
        print("  END-TO-END  (Retrieval + LLM)")
        print(f"{'─'*60}")
        print(f"  Samples              : {e2e['n_samples']}")
        print(f"  Top-K codes asked    : {e2e['top_k']}")
        print()
        print(f"  ICD-10  Precision    : {e2e['icd_precision']:.1%}")
        print(f"  ICD-10  Recall       : {e2e['icd_recall']:.1%}")
        print(f"  ICD-10  F1           : {e2e['icd_f1']:.1%}")
        print()
        print(f"  CPT     Precision    : {e2e['cpt_precision']:.1%}")
        print(f"  CPT     Recall       : {e2e['cpt_recall']:.1%}")
        print(f"  CPT     F1           : {e2e['cpt_f1']:.1%}")
        print()
        print(f"  Overall F1           : {e2e['overall_f1']:.1%}")
        print()
        print(f"  Confidence (correct) : {e2e['avg_confidence_when_correct']:.3f}")
        print(f"  Confidence (wrong)   : {e2e['avg_confidence_when_wrong']:.3f}")
        gap = e2e['calibration_gap']
        calibration_note = "well-calibrated ✓" if gap >= 0.05 else "poorly calibrated ⚠"
        print(f"  Calibration gap      : {gap:+.3f}  ({calibration_note})")
        print()
        print(f"  Avg latency          : {e2e['avg_latency_ms']} ms / note")

    print(f"\n{sep}\n")

    # Interpretation guide
    print("  INTERPRETATION GUIDE")
    print(f"{'─'*60}")
    print("  Retrieval Recall@K")
    print("    < 60%  → index too small or embedding model mismatch")
    print("    60-80% → acceptable; expand dataset or increase top-K")
    print("    > 80%  → retrieval is healthy")
    if e2e:
        print()
        print("  End-to-End F1")
        print("    < 40%  → LLM prompt or context needs work")
        print("    40-70% → typical for small index; grow dataset")
        print("    > 70%  → production-ready for assisted coding")
        print()
        print("  Calibration gap (correct conf − wrong conf)")
        print("    < 0.05 → model confidence is not meaningful")
        print("    ≥ 0.05 → confidence scores are trustworthy")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

async def main_async(args: argparse.Namespace) -> None:
    # Load dataset
    if args.dataset:
        dataset_path = Path(args.dataset)
        if not dataset_path.exists():
            sys.exit(f"Dataset file not found: {args.dataset}")
        with open(dataset_path, encoding="utf-8") as f:
            dataset = [json.loads(line) for line in f if line.strip()]
        print(f"Loaded {len(dataset)} samples from {args.dataset}")
    else:
        dataset = BUILTIN_DATASET
        print(f"Using built-in dataset ({len(dataset)} samples)")

    # Always run retrieval eval (no API cost)
    print("\n" + "═" * 60)
    print("  STEP 1 — Retrieval evaluation")
    print("═" * 60)
    retrieval_results = evaluate_retrieval(dataset, retrieval_k=args.retrieval_k)

    # Optionally run end-to-end eval
    e2e_results = None
    if not args.no_llm:
        print("\n" + "═" * 60)
        print("  STEP 2 — End-to-end evaluation  (calls Groq API)")
        print("═" * 60)
        e2e_results = await evaluate_end_to_end(
            dataset, top_k=args.top_k, retrieval_k=args.retrieval_k
        )

    # Print report
    print_report(retrieval_results, e2e_results)

    # Optionally save JSON
    if args.output:
        output = {
            "retrieval": retrieval_results,
            "end_to_end": e2e_results,
        }
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"Results saved to {args.output}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate RAG accuracy for the Medical Coding AI system"
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to a JSONL eval file. Omit to use the built-in 15-sample set.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of codes to request from the pipeline (default: 5)",
    )
    parser.add_argument(
        "--retrieval-k",
        type=int,
        default=10,
        help="FAISS top-K to check recall against (default: 10)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip the Groq LLM step — retrieval-only eval, no API cost",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write a JSON results file, e.g. eval_results.json",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
