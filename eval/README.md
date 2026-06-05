# Evaluation Harness

Reproducible measurement of the Medical Coding SaaS pipeline.
Produces the numbers that go into the **Results** section of the paper.

```
eval/
├── datasets/
│   ├── starter_gold.jsonl       # 20 synthetic coding examples (harness validation only)
│   ├── phi_test_set.jsonl       # 5 documents with labeled PHI spans
│   └── loader.py                # JSONL → python loaders
├── metrics.py                   # Recall@k, MRR, micro/macro PRF, per-chapter F1, PHI leakage
├── run_retrieval_eval.py        # FAISS shortlist quality (no LLM call, free)
├── run_e2e_eval.py              # Full pipeline with Groq (costs API calls)
├── run_phi_eval.py              # PHI leakage on labeled spans
├── run_all.py                   # Runs all three + writes results/report.md
└── results/                     # JSON + markdown output (git-ignored)
```

## Quick start

```bash
# 0. Build the FAISS index once (requires CMS dataset files):
python data_pipeline/scripts/preprocess.py
python data_pipeline/scripts/build_index.py \
    --input  data/processed/medical_codes_v2024.jsonl \
    --output data/vector_stores/faiss_index

# 1. Offline stages only (no API key needed):
python -m eval.run_retrieval_eval --gold eval/datasets/starter_gold.jsonl
python -m eval.run_phi_eval       --gold eval/datasets/phi_test_set.jsonl

# 2. Full end-to-end (requires GROQ_API_KEY):
export GROQ_API_KEY=sk-...
python -m eval.run_all
```

## Benchmarks to plug in

The starter gold set is **only 20 synthetic notes** — enough to validate
the harness, not enough to claim a real accuracy number. For a
publication-grade result, load one of:

| Dataset | Size | Access | Loader |
|---|---|---|---|
| **CodiEsp** (ICD-10 on Spanish case reports) | ~1,000 docs | CC-BY, free | convert to `gold_icd10` JSONL |
| **MIMIC-IV-CDM / MIMIC-IV-Note** | 10K+ discharge summaries with ICD-10 | PhysioNet credentialed | use `notes_icd.jsonl` converter |
| **i2b2 2014 de-identification** | PHI gold spans | DUA required | maps directly to `phi_test_set.jsonl` shape |

Target JSONL shape:

```jsonl
{"id": "doc_001", "text": "...", "gold_icd10": ["E11.9"], "gold_cpt": ["99213"]}
{"id": "phi_001", "text": "...", "phi_spans": ["John Smith", "2024-01-15"]}
```

## Metrics produced

**Retrieval** — whether the gold code is in the FAISS top-k:
- Recall@{1,5,10,20}, Precision@{1,5}, MRR
- Throughput (queries/sec)

**End-to-end coding** — LLM output vs gold:
- Micro & macro Precision / Recall / F1 (standard ICD-10 multi-label metrics)
- Per-chapter micro-F1 (long-tail analysis)
- Latency mean / p50 / p95

**PHI leakage** — verbatim survival of labeled PHI spans:
- Leakage rate (leaked / total) — lower is better
- Recall (1 − leakage) — HIPAA-facing number

## Honest reporting guidelines

1. **Never report numbers from `starter_gold.jsonl` as the paper's headline.**
   It exists to prove the harness runs, not to benchmark the system.
2. Always print **n**, the test set, and the index build version alongside
   any accuracy figure.
3. Keep `results/*.json` under version control for the run that produces
   the paper's numbers (or archive a zip).
4. Report confidence intervals with bootstrap resampling over
   `per_example` when N < 200.
