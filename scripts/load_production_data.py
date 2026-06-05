"""
Production Data Loader
━━━━━━━━━━━━━━━━━━━━━
Loads the full ICD-10-CM and HCPCS datasets, preprocesses them,
generates embeddings, and builds/updates the FAISS index.

Usage:
  python scripts/load_production_data.py \
    --icd10 ./data/icd10/icd10cm_order_2024.txt \
    --hcpcs ./data/hcpcs/HCPCS2024_ANWEB.csv \
    --output-index ./backend/data/vector_stores/faiss_index

Data downloads:
  ICD-10-CM: https://www.cms.gov/medicare/coding-billing/icd-10-codes
  HCPCS:     https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-coding-system
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "data_pipeline" / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "data_pipeline" / "scripts"))

from preprocess import parse_icd10cm_flat, parse_hcpcs, clean_records, save_processed_dataset
from build_index import load_jsonl, generate_embeddings, build_faiss_index, save_index, test_search

from sentence_transformers import SentenceTransformer
from loguru import logger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--icd10",        required=True, help="Path to ICD-10-CM flat file")
    parser.add_argument("--hcpcs",        required=True, help="Path to HCPCS CSV file")
    parser.add_argument("--output-index", required=True, help="Output FAISS index path")
    parser.add_argument("--model",        default="sentence-transformers/all-MiniLM-L6-v2")
    args = parser.parse_args()

    # Step 1: Parse
    logger.info("Step 1/4: Parsing datasets...")
    icd_records = parse_icd10cm_flat(args.icd10)
    hcpcs_records = parse_hcpcs(args.hcpcs)
    logger.info(f"  ICD-10: {len(icd_records):,} | HCPCS: {len(hcpcs_records):,}")

    # Step 2: Clean
    logger.info("Step 2/4: Cleaning and deduplicating...")
    all_records = clean_records(icd_records + hcpcs_records)

    # Step 3: Save processed
    processed_path = "./data/processed/medical_codes_v2024.jsonl"
    save_processed_dataset(all_records, processed_path)

    # Step 4: Embed + index
    logger.info("Step 3/4: Generating embeddings...")
    model = SentenceTransformer(args.model)
    texts = [r["text"] for r in all_records]
    embeddings = generate_embeddings(texts, model)

    logger.info("Step 4/4: Building FAISS index...")
    index = build_faiss_index(embeddings)
    save_index(index, all_records, args.output_index)

    test_search(index, all_records, model)
    logger.info(f"Done! {len(all_records):,} codes indexed.")


if __name__ == "__main__":
    main()
