"""
FAISS Index Builder
━━━━━━━━━━━━━━━━━━
Reads the processed JSONL dataset, generates embeddings,
and builds/saves the FAISS index for the RAG pipeline.

Run:
  python build_index.py --input ./data/processed/medical_codes_v2024.jsonl \
                        --output ./data/vector_stores/faiss_index

Tokenization Strategy:
  We use sentence-transformers (SentenceTransformer) which handles its own
  tokenization internally using WordPiece/BPE. Key choices:
  - Model: all-MiniLM-L6-v2 (384-dim) — fast, works well on medical text
  - Max sequence length: 256 tokens (covers 99% of code descriptions)
  - For longer clinical examples: mean pooling over sliding windows
  - Alternative for production: pritamdeka/PubMedBERT-mnli-snli-scinli (768-dim,
    trained on biomedical text — use if accuracy needs improvement)
"""

import argparse
import json
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.error("FAISS not installed: pip install faiss-cpu")


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 256  # Tune based on available RAM; larger = faster
EMBEDDING_DIM = 384


def load_jsonl(path: str) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    logger.info(f"Loaded {len(records)} records from {path}")
    return records


def generate_embeddings(
    texts: list[str],
    model: SentenceTransformer,
    batch_size: int = BATCH_SIZE,
) -> np.ndarray:
    """
    Encode texts in batches with progress bar.
    normalize_embeddings=True → cosine similarity via inner product.
    """
    logger.info(f"Generating embeddings for {len(texts)} texts...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return embeddings.astype("float32")


def build_faiss_index(embeddings: np.ndarray) -> "faiss.Index":
    """
    IndexFlatIP: exact inner product search (= cosine on normalized vecs).
    For >500K entries: use IndexIVFFlat(quantizer, dim, nlist=1024)
    with nprobe=32 for ANN search — 50× faster with <1% recall drop.
    """
    if not FAISS_AVAILABLE:
        raise RuntimeError("FAISS not available")
    n, dim = embeddings.shape
    index = faiss.IndexFlatIP(dim)
    logger.info(f"Building FAISS IndexFlatIP — {n} vectors × {dim} dims")
    index.add(embeddings)
    logger.info(f"Index built: {index.ntotal} vectors")
    return index


def save_index(index: "faiss.Index", metadata: list[dict], output_path: str) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(out))
    meta_path = out.with_suffix(".meta.pkl")
    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)

    logger.info(f"Index saved: {out}")
    logger.info(f"Metadata saved: {meta_path}")
    logger.info(f"Index size on disk: {out.stat().st_size / 1024 / 1024:.1f} MB")


def test_search(
    index: "faiss.Index",
    metadata: list[dict],
    model: SentenceTransformer,
    query: str = "Type 2 diabetes mellitus without complications",
    top_k: int = 5,
) -> None:
    """Quick sanity-check of the built index."""
    query_vec = model.encode([query], normalize_embeddings=True).astype("float32")
    scores, indices = index.search(query_vec, top_k)

    logger.info(f"\nTest query: '{query}'")
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0:
            m = metadata[idx]
            logger.info(f"  [{score:.3f}] {m['code']}: {m['description'][:80]}")


def main():
    parser = argparse.ArgumentParser(description="Build FAISS index for medical codes")
    parser.add_argument("--input", required=True, help="Path to processed JSONL file")
    parser.add_argument("--output", required=True, help="Output path for FAISS index")
    parser.add_argument("--model", default=EMBEDDING_MODEL, help="Embedding model name")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    # Load data
    records = load_jsonl(args.input)
    if not records:
        raise SystemExit(
            "Input dataset is empty. Run preprocess with valid CMS source files first, "
            "then rerun build_index."
        )

    # Load model
    logger.info(f"Loading embedding model: {args.model}")
    model = SentenceTransformer(args.model)

    # Extract texts
    texts = [r["text"] for r in records]

    # Generate embeddings
    embeddings = generate_embeddings(texts, model, batch_size=args.batch_size)

    # Build index
    index = build_faiss_index(embeddings)

    # Save
    save_index(index, records, args.output)

    # Sanity check
    test_search(index, records, model)

    logger.info("Index build complete!")


if __name__ == "__main__":
    main()
