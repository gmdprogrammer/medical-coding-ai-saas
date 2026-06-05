"""
Medical Coding Data Preprocessing Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dataset Sources (all publicly available):

ICD-10-CM:
  https://www.cms.gov/medicare/coding-billing/icd-10-codes/2024-icd-10-cm
  → Download "FY2024 April 1 Addenda Code Descriptions in Tabular Order"
  → File: icd10cm_tabular_2024.xml  OR  icd10cm_codes_addenda_2024.txt

ICD-10-PCS (procedures):
  https://www.cms.gov/medicare/coding-billing/icd-10-codes/2024-icd-10-pcs-and-gems
  → File: icd10pcs_codes_2024.txt

HCPCS Level II (CPT alternative, fully public):
  https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-coding-system
  → File: HCPCS2024_ANWEB_v3.zip

MIMIC-III Clinical Notes (requires credentialed PhysioNet access):
  https://physionet.org/content/mimiciii/1.4/
  → NOTEEVENTS.csv (filtered to DISCHARGE SUMMARY)
  → After access: anonymized clinical text for RAG examples

Data Schema Design:
  {
    "code_type": "icd10" | "icd10pcs" | "hcpcs",
    "code": str,          # e.g., "E11.9"
    "description": str,   # full description
    "short_desc": str,    # abbreviated
    "category": str,      # chapter / section
    "billable": bool,
    "clinical_notes": str,  # optional example usage
    "text": str,          # embedding input = description + clinical_notes
    "version": str,       # dataset version e.g. "2024"
  }
"""

import csv
import json
import re
import zipfile
from pathlib import Path
from typing import Iterator

import pandas as pd
from loguru import logger


# ── ICD-10-CM Parser ──────────────────────────────────────────────────────────

def parse_icd10cm_flat(filepath: str) -> list[dict]:
    """
    Parse the CMS flat-file format:
      FIELD 1: Order number
      FIELD 2: Code (no decimal)
      FIELD 3: Valid for submission (1=yes, 0=header)
      FIELD 4: Short description
      FIELD 5: Long description
    """
    records = []
    path = Path(filepath)
    if not path.exists():
        logger.warning(f"ICD-10 file not found: {filepath}")
        return []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            parts = line.split("\t")
            if len(parts) >= 5:
                _, raw_code, billable, short_desc, long_desc = parts[:5]
            else:
                # CMS order files are often fixed-width in local downloads.
                # Example:
                # 00002 A000    1 <short desc>    <long desc>
                m = re.match(r"^\s*\d+\s+([A-Z0-9]+)\s+([01])\s+(.+?)\s{2,}(.+)$", line)
                if not m:
                    continue
                raw_code, billable, short_desc, long_desc = m.groups()
            # Insert decimal: E119 → E11.9
            code = _format_icd10_code(raw_code.strip())
            records.append({
                "code_type": "icd10",
                "code": code,
                "description": long_desc.strip(),
                "short_desc": short_desc.strip(),
                "category": code[:3],
                "billable": billable.strip() == "1",
                "clinical_notes": "",
                "text": f"{code}: {long_desc.strip()}",
                "version": "2024",
            })

    logger.info(f"Parsed {len(records)} ICD-10-CM codes")
    return records


def _format_icd10_code(raw: str) -> str:
    """Insert decimal after position 3 for ICD-10 codes."""
    raw = raw.strip()
    if len(raw) > 3:
        return f"{raw[:3]}.{raw[3:]}"
    return raw


# ── HCPCS Level II Parser ─────────────────────────────────────────────────────

def parse_hcpcs(filepath: str) -> list[dict]:
    """
    Parse CMS HCPCS Level II annual update file.
    CSV columns: HCPC, SEQNUM, RECID, LONG_DESCRIPTION, SHORT_DESCRIPTION, ...
    """
    records = []
    path = Path(filepath)
    if not path.exists():
        logger.warning(f"HCPCS file not found: {filepath}")
        return []

    try:
        df = pd.read_csv(path, dtype=str, encoding="latin-1")
        df.columns = [c.strip().upper() for c in df.columns]

        for _, row in df.iterrows():
            code = str(row.get("HCPC", "")).strip()
            desc = str(row.get("LONG_DESCRIPTION", row.get("SHORT_DESCRIPTION", ""))).strip()
            if not code or not desc or code == "nan":
                continue
            records.append({
                "code_type": "hcpcs",
                "code": code,
                "description": desc,
                "short_desc": str(row.get("SHORT_DESCRIPTION", "")).strip(),
                "category": code[0],  # Letter prefix = category
                "billable": True,
                "clinical_notes": "",
                "text": f"{code}: {desc}",
                "version": "2024",
            })
    except Exception:
        # Fallback for CMS fixed-width Alpha-Numeric HCPCS text files.
        # Official CMS record layout: cols 0-4=HCPC, 5-7=SEQNUM, 8-10=RECID,
        # 11-RECID+1=long desc (varies), then short desc.
        # We skip the 3-char RECID prefix in the rest field.
        merged: dict[str, dict] = {}
        with open(path, encoding="latin-1") as f:
            for line in f:
                line = line.rstrip("\n")
                m = re.match(r"^\s*([A-Z0-9]{5})(\d{3})(.*)$", line)
                if not m:
                    continue
                code, _seq, rest = m.groups()
                # Strip the 3-char RECID that starts the rest field (e.g. "003")
                if len(rest) >= 3 and rest[:3].isdigit():
                    rest = rest[3:]
                long_desc = rest[:120].strip()
                short_desc = rest[120:180].strip()
                if not long_desc and not short_desc:
                    continue
                entry = merged.setdefault(code, {"long_parts": [], "short_parts": []})
                if long_desc:
                    entry["long_parts"].append(long_desc)
                if short_desc:
                    entry["short_parts"].append(short_desc)

        for code, value in merged.items():
            desc = " ".join(value["long_parts"]).strip()
            short_desc = " ".join(value["short_parts"]).strip()
            if not desc:
                continue
            records.append({
                "code_type": "hcpcs",
                "code": code,
                "description": desc,
                "short_desc": short_desc,
                "category": code[0],
                "billable": True,
                "clinical_notes": "",
                "text": f"{code}: {desc}",
                "version": "2024",
            })

    logger.info(f"Parsed {len(records)} HCPCS codes")
    return records


# ── Clinical Synonym Enrichment ───────────────────────────────────────────────

# Maps substrings in code descriptions to additional clinical terms that
# clinicians actually write in notes. This bridges the vocabulary gap between
# formal ICD-10 language and real clinical text.
_SYNONYM_MAP: list[tuple[str, str]] = [
    ("diabetes mellitus", "diabetes diabetic blood sugar glucose insulin HbA1c A1c"),
    ("hypertension", "high blood pressure elevated BP HTN"),
    ("pneumonia", "lung infection chest infection respiratory infection consolidation"),
    ("chronic kidney disease", "CKD renal failure kidney failure renal insufficiency"),
    ("hyperlipidemia", "high cholesterol dyslipidemia elevated lipids LDL triglycerides"),
    ("myocardial infarction", "heart attack MI STEMI NSTEMI cardiac event"),
    ("heart failure", "CHF congestive heart failure reduced ejection fraction HFrEF"),
    ("asthma", "wheezing bronchospasm reactive airway disease"),
    ("depression", "depressive disorder low mood PHQ-9 antidepressant"),
    ("obesity", "overweight BMI body mass index weight management"),
    ("hypothyroidism", "underactive thyroid TSH levothyroxine thyroid hormone"),
    ("anemia", "low hemoglobin low hematocrit iron deficiency CBC"),
    ("upper respiratory", "cold URI rhinorrhea sore throat nasal congestion"),
    ("office visit", "outpatient visit clinic visit established patient follow-up"),
    ("chest x-ray", "chest radiograph CXR chest film PA lateral"),
    ("electrocardiogram", "ECG EKG 12-lead cardiac rhythm"),
    ("complete blood count", "CBC blood count hemoglobin hematocrit WBC platelets"),
    ("metabolic panel", "CMP BMP electrolytes glucose BUN creatinine liver function"),
]


def _get_clinical_synonyms(code: str, description: str) -> str:
    """Return a string of clinical synonyms relevant to this code's description."""
    desc_lower = description.lower()
    matched: list[str] = []
    for keyword, synonyms in _SYNONYM_MAP:
        if keyword in desc_lower:
            matched.append(synonyms)
    return " ".join(matched)


# ── Data Cleaning ─────────────────────────────────────────────────────────────

def clean_records(records: list[dict]) -> list[dict]:
    """
    Apply data quality rules:
    1. Remove codes without descriptions
    2. Normalize whitespace
    3. Filter non-billable header codes
    4. Remove duplicates by code
    5. Enrich text field with synonyms/context
    """
    seen_codes: set[str] = set()
    cleaned: list[dict] = []

    for rec in records:
        code = rec.get("code", "").strip()
        desc = rec.get("description", "").strip()

        # Rule 1: Skip blank descriptions
        if not code or not desc or desc.lower() in ("nan", "n/a", ""):
            continue

        # Rule 3: Skip non-billable header codes
        if not rec.get("billable", True):
            continue

        # Rule 4: Dedup
        if code in seen_codes:
            continue
        seen_codes.add(code)

        # Rule 2: Normalize whitespace
        rec["description"] = re.sub(r"\s+", " ", desc)
        rec["short_desc"] = re.sub(r"\s+", " ", rec.get("short_desc", ""))

        # Rule 5: Enrich embedding text with code + both descriptions + clinical synonyms
        # The richer the text field, the better semantic search works for
        # colloquial clinical language ("high sugar" → E11.9, "chest pain" → I20.9)
        synonyms = _get_clinical_synonyms(code, rec["description"])
        rec["text"] = (
            f"Medical code {code}: {rec['description']}. "
            f"Also known as: {rec['short_desc']}. "
            f"{synonyms}"
        ).strip(". ").strip()

        cleaned.append(rec)

    logger.info(f"After cleaning: {len(cleaned)} records (from {len(records)})")
    return cleaned


# ── Class Imbalance Handling ──────────────────────────────────────────────────

def analyze_category_distribution(records: list[dict]) -> pd.DataFrame:
    """
    ICD-10 has severe class imbalance:
    Chapter I (Infectious): ~2.5K codes
    Chapter XIX (Injury/Trauma): ~30K codes (12× more)

    Strategy:
    - For vector search: imbalance is acceptable — semantic search naturally
      weights relevance over frequency.
    - For fine-tuning classification: apply stratified sampling and
      class-weighted loss (weight_i = total / (num_classes * count_i)).
    """
    if not records:
        return pd.DataFrame(columns=["code_type", "category", "count", "weight"])
    df = pd.DataFrame(records)
    dist = df.groupby(["code_type", "category"]).size().reset_index(name="count")
    dist["weight"] = dist.groupby("code_type")["count"].transform(
        lambda x: x.sum() / (len(x) * x)
    )
    return dist


# ── Dataset Versioning ────────────────────────────────────────────────────────

def save_processed_dataset(records: list[dict], output_path: str, version: str = "2024") -> None:
    """
    Save cleaned records as versioned JSONL.
    Versioning strategy: append fiscal year to filename.
    Use DVC (Data Version Control) for git-based dataset tracking in production.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    versioned_path = path.parent / f"{path.stem}_v{version}{path.suffix}"

    with open(versioned_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    # Write manifest
    manifest = {
        "version": version,
        "total_records": len(records),
        "by_type": {
            code_type: sum(1 for r in records if r["code_type"] == code_type)
            for code_type in ["icd10", "icd10pcs", "hcpcs"]
        },
    }
    manifest_path = path.parent / f"manifest_v{version}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Saved {len(records)} records → {versioned_path}")
    logger.info(f"Manifest: {manifest}")


def load_dataset(jsonl_path: str) -> list[dict]:
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


if __name__ == "__main__":
    import sys
    icd_path = sys.argv[1] if len(sys.argv) > 1 else "./datasets/icd10/icd10cm_order_2024.txt"
    hcpcs_path = sys.argv[2] if len(sys.argv) > 2 else "./datasets/hcpcs/HCPCS2024_ANWEB.csv"

    icd_records = parse_icd10cm_flat(icd_path)
    hcpcs_records = parse_hcpcs(hcpcs_path)
    all_records = clean_records(icd_records + hcpcs_records)

    save_processed_dataset(all_records, "./data/processed/medical_codes.jsonl")
    dist = analyze_category_distribution(all_records)
    if dist.empty:
        logger.warning(
            "No records available for distribution analysis. "
            "Place CMS files under ./datasets/icd10 and ./datasets/hcpcs or pass explicit file paths."
        )
    else:
        logger.info(f"\nCategory distribution sample:\n{dist.head(20).to_string()}")
