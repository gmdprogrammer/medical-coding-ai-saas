"""
BM25 baseline retriever
━━━━━━━━━━━━━━━━━━━━━━━
Lexical (sparse) retriever over the same cleaned CMS corpus that backs the
dense FAISS index. Provided as a baseline for §4.9 of the paper.

Implementation notes
  • Tokenisation: lowercase + non-alphanumeric split (regex `[a-z0-9]+`).
    Avoids spaCy/NLTK runtime cost; works well on short code descriptions.
  • Algorithm: Okapi BM25 (rank_bm25.BM25Okapi), k1=1.5, b=0.75 (defaults).
  • Corpus: same JSONL produced by data_pipeline/scripts/preprocess.py
    so retrieval scope is identical to the dense pipeline.
  • API surface: `search()`, `search_icd10()`, `search_cpt()` — drop-in
    compatible with `app.services.vector_store.VectorStore`.

Install: `pip install rank-bm25==0.2.2`
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from loguru import logger

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank_bm25 not installed — BM25 baseline unavailable")


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Retriever:
    """BM25 retriever with the same surface area as the dense VectorStore."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        if not BM25_AVAILABLE:
            raise RuntimeError("rank_bm25 not available — `pip install rank-bm25==0.2.2`")
        self._k1 = k1
        self._b = b
        self._bm25: BM25Okapi | None = None
        self._metadata: list[dict] = []

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def load_corpus(self, jsonl_path: str | Path) -> None:
        """Load the same JSONL the dense index was built from."""
        records: list[dict] = []
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        if not records:
            raise ValueError(f"BM25 corpus is empty: {jsonl_path}")

        tokenised = [_tokenize(r["text"]) for r in records]
        self._bm25 = BM25Okapi(tokenised, k1=self._k1, b=self._b)
        self._metadata = records
        logger.info(f"BM25 index built — {len(records)} documents, "
                    f"avg doc len = {sum(len(t) for t in tokenised) / len(tokenised):.1f} tokens")

    @property
    def total_documents(self) -> int:
        return len(self._metadata)

    @property
    def icd10_count(self) -> int:
        return sum(1 for m in self._metadata if m.get("code_type") == "icd10")

    @property
    def cpt_count(self) -> int:
        return sum(1 for m in self._metadata if m.get("code_type") in ("cpt", "hcpcs"))

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 10,
        code_type: str | None = None,
        min_score: float = 0.0,
    ) -> list[dict]:
        if self._bm25 is None or not self._metadata:
            return []

        scores = self._bm25.get_scores(_tokenize(query))
        # Over-fetch to recover from the categorical filter, mirroring the dense path.
        n_fetch = min(top_k * 5, len(scores))
        # argpartition is O(n); we then sort the small slice.
        import numpy as np
        idx = np.argpartition(-scores, n_fetch - 1)[:n_fetch]
        idx = idx[np.argsort(-scores[idx])]

        results: list[dict] = []
        for i in idx:
            score = float(scores[i])
            if score < min_score:
                continue
            meta = self._metadata[i].copy()
            if code_type and meta.get("code_type") != code_type:
                continue
            meta["score"] = score
            results.append(meta)
            if len(results) >= top_k:
                break
        return results

    def search_icd10(self, query: str, top_k: int = 10) -> list[dict]:
        return self.search(query, top_k=top_k, code_type="icd10")

    def search_cpt(self, query: str, top_k: int = 10) -> list[dict]:
        # Returns both 'cpt' and 'hcpcs' entries to mirror the dense pipeline.
        results = self.search(query, top_k=top_k * 2)
        return [r for r in results if r.get("code_type") in ("cpt", "hcpcs")][:top_k]
