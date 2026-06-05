"""
Hybrid retrieval baseline (Reciprocal Rank Fusion)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fuses BM25 (lexical) and dense (FAISS) rankings with RRF (Cormack et al. 2009):

    RRF_score(d) = Σ_r  1 / (k + rank_r(d))

with k = 60 (standard). The retriever returns the top-k documents by fused
score, restricted to a `code_type` if requested.
"""
from __future__ import annotations

from typing import Any


class HybridRRFRetriever:
    """Reciprocal Rank Fusion of any two rankers exposing `.search()`."""

    def __init__(self, dense, sparse, k: int = 60) -> None:
        self._dense = dense
        self._sparse = sparse
        self._k = k

    def _fuse(self, dense_hits: list[dict], sparse_hits: list[dict], top_k: int) -> list[dict]:
        bucket: dict[str, dict[str, Any]] = {}

        for rank, h in enumerate(dense_hits, start=1):
            key = f"{h.get('code_type')}::{h['code']}"
            bucket.setdefault(key, {"meta": h, "rrf": 0.0})
            bucket[key]["rrf"] += 1.0 / (self._k + rank)

        for rank, h in enumerate(sparse_hits, start=1):
            key = f"{h.get('code_type')}::{h['code']}"
            bucket.setdefault(key, {"meta": h, "rrf": 0.0})
            bucket[key]["rrf"] += 1.0 / (self._k + rank)

        merged = sorted(bucket.values(), key=lambda x: x["rrf"], reverse=True)
        out: list[dict] = []
        for entry in merged[:top_k]:
            m = dict(entry["meta"])
            m["score"] = entry["rrf"]
            out.append(m)
        return out

    def search_icd10(self, query: str, top_k: int = 10) -> list[dict]:
        d = self._dense.search_icd10(query, top_k=top_k * 2)
        s = self._sparse.search_icd10(query, top_k=top_k * 2)
        return self._fuse(d, s, top_k)

    def search_cpt(self, query: str, top_k: int = 10) -> list[dict]:
        d = self._dense.search_cpt(query, top_k=top_k * 2)
        s = self._sparse.search_cpt(query, top_k=top_k * 2)
        return self._fuse(d, s, top_k)
