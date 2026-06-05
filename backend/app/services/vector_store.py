"""
FAISS-backed Vector Store for Medical Codes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stores embeddings for:
  • ICD-10 code descriptions
  • CPT / HCPCS procedure descriptions
  • Clinical example snippets

Embedding Model: sentence-transformers/all-MiniLM-L6-v2
  → 384-dimensional dense vectors
  → 5× faster than large models, strong on clinical text
  → Outperforms BM25 for semantic similarity in medical domain

Search strategy: cosine similarity with a minimum threshold filter.
"""
from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not installed — vector search unavailable")

from app.config import get_settings

settings = get_settings()


class VectorStore:
    """
    Thread-safe FAISS index wrapper with metadata storage.

    Index type: IndexFlatIP (inner product on L2-normalized vectors = cosine sim).
    For large corpora (>1M entries) swap to IndexIVFFlat with nlist=1024.
    """

    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None
        self._index: Any | None = None          # faiss.Index
        self._metadata: list[dict] = []         # parallel array to index rows
        self._index_path = Path(settings.faiss_index_path)
        self._meta_path = self._index_path.with_suffix(".meta.pkl")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        self._model = SentenceTransformer(settings.embedding_model)
        if self._index_path.exists() and self._meta_path.exists():
            self._load()
            logger.info(f"Vector store loaded — {len(self._metadata)} entries")
        else:
            self._create_empty_index()
            logger.info("Empty FAISS index created")

    def _create_empty_index(self) -> None:
        if not FAISS_AVAILABLE:
            return
        dim = settings.embedding_dimension
        self._index = faiss.IndexFlatIP(dim)
        self._metadata = []

    def _load(self) -> None:
        if not FAISS_AVAILABLE:
            return
        self._index = faiss.read_index(str(self._index_path))
        with open(self._meta_path, "rb") as f:
            self._metadata = pickle.load(f)
        # Strip RECID prefix (e.g. "003") that leaked into some HCPCS descriptions
        # during initial indexing — fix in-memory so re-indexing is not required.
        import re as _re
        # Matches a 3-digit RECID at the very start, or embedded mid-string
        # when continuation lines were concatenated (e.g. "...text 003more text")
        _recid = _re.compile(r"(?:^|\s)\d{3}(?=[A-Z])")
        for m in self._metadata:
            if m.get("code_type") == "hcpcs":
                m["description"] = _recid.sub(" ", m["description"]).strip()
                m["text"] = _recid.sub(" ", m["text"]).strip()

    def save(self) -> None:
        if not FAISS_AVAILABLE or self._index is None:
            return
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._index_path))
        with open(self._meta_path, "wb") as f:
            pickle.dump(self._metadata, f)
        logger.info(f"Vector store saved — {len(self._metadata)} entries")

    # ── Indexing ──────────────────────────────────────────────────────────────

    def add_documents(self, documents: list[dict]) -> None:
        """
        Add a batch of documents.  Each dict must have:
          code_type  : "icd10" | "cpt" | "hcpcs"
          code       : str
          description: str
          text       : str   (description + additional context concatenated)
        """
        if not FAISS_AVAILABLE or self._model is None:
            logger.warning("Cannot add documents: FAISS or model not initialized")
            return
        texts = [doc["text"] for doc in documents]
        embeddings = self._embed(texts)
        self._index.add(embeddings)
        self._metadata.extend(documents)
        logger.debug(f"Added {len(documents)} documents to vector store")

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 10,
        code_type: str | None = None,
        min_score: float = 0.3,
    ) -> list[dict]:
        """
        Semantic search over the index.
        Returns metadata dicts augmented with a `score` field.
        """
        if not FAISS_AVAILABLE or self._index is None or self._index.ntotal == 0:
            return []

        query_vec = self._embed([query])
        k = min(top_k * 3, self._index.ntotal)  # over-fetch for post-filter
        scores, indices = self._index.search(query_vec, k)

        results: list[dict] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or score < min_score:
                continue
            meta = self._metadata[idx].copy()
            meta["score"] = float(score)
            if code_type and meta.get("code_type") != code_type:
                continue
            results.append(meta)
            if len(results) >= top_k:
                break

        return sorted(results, key=lambda x: x["score"], reverse=True)

    def search_icd10(self, query: str, top_k: int = 10) -> list[dict]:
        return self.search(query, top_k=top_k, code_type="icd10")

    def search_cpt(self, query: str, top_k: int = 10) -> list[dict]:
        # The index stores procedure codes as "hcpcs" (public CMS dataset).
        # "cpt" is the AMA-restricted label — it never appears in the index.
        # Searching for "cpt" always returned [] which silently broke the pipeline.
        return self.search(query, top_k=top_k, code_type="hcpcs")

    # ── Embedding ──────────────────────────────────────────────────────────────

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Encode and L2-normalize for cosine similarity via inner product."""
        vecs = self._model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return np.array(vecs, dtype="float32")

    # ── Stats ─────────────────────────────────────────────────────────────────

    @property
    def total_documents(self) -> int:
        return len(self._metadata)

    @property
    def icd10_count(self) -> int:
        return sum(1 for m in self._metadata if m.get("code_type") == "icd10")

    @property
    def cpt_count(self) -> int:
        # Codes are stored as "hcpcs" (public CMS equivalent of CPT)
        return sum(1 for m in self._metadata if m.get("code_type") in ("cpt", "hcpcs"))


# Singleton
_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
        _store.initialize()
    return _store
