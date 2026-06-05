"""
Gold-set loaders for evaluation.

Supported formats (all JSONL, one record per line):

  Coding eval:
    {
      "id": "doc_001",
      "text": "Clinical note text...",
      "gold_icd10": ["E11.9", "I10"],
      "gold_cpt":   ["99213"]     # optional, may be []
    }

  PHI eval:
    {
      "id": "phi_001",
      "text": "Patient John Doe, MRN 12345...",
      "phi_spans": ["John Doe", "12345", "2024-01-15"]
    }

Datasets:
  • starter_gold.jsonl  — 20 hand-crafted synthetic notes shipped in-repo
                          (for harness validation; NOT a real benchmark)
  • codiesp / mimic_iv  — loaders provided; users must download the data
                          separately due to licensing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def load_jsonl(path: str | Path) -> list[dict]:
    records: list[dict] = []
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Gold set not found: {p}")
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def iter_coding_examples(path: str | Path) -> Iterator[dict]:
    for rec in load_jsonl(path):
        yield {
            "id": rec.get("id", ""),
            "text": rec["text"],
            "gold_icd10": set(rec.get("gold_icd10", [])),
            "gold_cpt": set(rec.get("gold_cpt", [])),
        }


def iter_phi_examples(path: str | Path) -> Iterator[dict]:
    for rec in load_jsonl(path):
        yield {
            "id": rec.get("id", ""),
            "text": rec["text"],
            "phi_spans": list(rec.get("phi_spans", [])),
        }
