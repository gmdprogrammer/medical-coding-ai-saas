"""
Retrieval-Augmented Generation (RAG) Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pipeline steps:
  1. Anonymize input (PHI removal)
  2. Embed query using sentence-transformers
  3. Retrieve top-K ICD-10 and CPT candidates from FAISS
  4. Build a structured context block for the LLM
  5. Call Groq LLM for final code extraction
  6. Post-process and validate output

Why RAG instead of pure fine-tuning?
  • Medical codes change annually — RAG updates by re-indexing, no retraining
  • Fine-tuning is expensive and requires large labeled datasets
  • RAG gives explicit citations per code (auditability requirement)
  • Use fine-tuning ONLY when RAG accuracy plateaus after dataset expansion
    (typically when you have >50K annotated clinical examples with gold codes)
"""
from __future__ import annotations

import time
from typing import Any

from loguru import logger

from app.core.phi_anonymizer import get_anonymizer, AnonymizationResult
from app.services.vector_store import get_vector_store
from app.services.groq_service import get_groq_service
from app.schemas.coding import MedicalCode, CodingResponse
from app.config import get_settings

settings = get_settings()

_CONFIDENCE_LABELS = {
    lambda c: c >= 0.85: "High",
    lambda c: c >= 0.65: "Medium",
    lambda c: c < 0.65: "Low",
}


def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "High"
    if score >= 0.65:
        return "Medium"
    return "Low"


def _build_rag_context(icd_results: list[dict], cpt_results: list[dict]) -> str:
    """
    Format retrieved medical codes into a structured context block.
    Rank position and score tier are shown explicitly so the LLM can
    weight high-similarity results more heavily.
    """
    def _score_tier(score: float) -> str:
        if score >= 0.80:
            return "★★★ very high match"
        if score >= 0.65:
            return "★★  high match"
        if score >= 0.50:
            return "★   moderate match"
        return "    low match"

    lines = ["=== RELEVANT ICD-10 CODES FROM KNOWLEDGE BASE (ranked by similarity) ==="]
    for rank, r in enumerate(icd_results, 1):
        lines.append(
            f"#{rank}  {r['code']} — {r['description']}  [{_score_tier(r['score'])}]"
        )
        if r.get("clinical_notes"):
            lines.append(f"     Clinical notes: {r['clinical_notes']}")

    lines.append("\n=== RELEVANT CPT/HCPCS CODES FROM KNOWLEDGE BASE (ranked by similarity) ===")
    for rank, r in enumerate(cpt_results, 1):
        lines.append(
            f"#{rank}  {r['code']} — {r['description']}  [{_score_tier(r['score'])}]"
        )
        if r.get("clinical_notes"):
            lines.append(f"     Clinical notes: {r['clinical_notes']}")

    return "\n".join(lines)


def _extract_clinical_queries(text: str) -> list[str]:
    """
    Break a clinical note into focused sub-queries for retrieval.
    Embedding a short, specific phrase retrieves far better than embedding
    the full note (which averages out to a blurry centroid).

    Strategy:
      1. Always include the full note (catches holistic matches)
      2. Split on sentence boundaries and keep sentences that contain
         clinical signal words (diagnosis, procedure, lab, symptom keywords)
      3. Cap at 6 queries to avoid over-fetching
    """
    import re as _re

    # Clinical signal words — sentences containing these are worth querying
    SIGNAL_PATTERN = _re.compile(
        r"\b(diagnos|disorder|disease|syndrome|failure|infection|injury|fracture|"
        r"cancer|tumor|diabetes|hypertension|asthma|pneumonia|anemia|"
        r"procedure|surgery|biopsy|excision|repair|replacement|transplant|"
        r"administered|prescribed|ordered|performed|obtained|"
        r"lab|panel|test|x-ray|radiograph|ecg|ekg|echo|mri|ct scan|"
        r"mg|mcg|units|dose|therapy|treatment)\b",
        _re.IGNORECASE,
    )

    sentences = _re.split(r"(?<=[.!?])\s+", text.strip())
    clinical_sentences = [s.strip() for s in sentences if SIGNAL_PATTERN.search(s)]

    queries = [text]  # always include full note
    queries.extend(clinical_sentences[:5])  # up to 5 focused sentences
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        if q not in seen and len(q) > 10:
            seen.add(q)
            unique.append(q)
    return unique[:6]


def _multi_query_search(
    search_fn,
    queries: list[str],
    top_k: int,
) -> list[dict]:
    """
    Run multiple queries and merge results, keeping the highest score
    per code to avoid duplicates.
    """
    best: dict[str, dict] = {}
    per_query_k = max(top_k, 5)  # fetch enough per query to have good coverage
    for query in queries:
        for result in search_fn(query, top_k=per_query_k):
            code = result["code"]
            if code not in best or result["score"] > best[code]["score"]:
                best[code] = result
    return sorted(best.values(), key=lambda x: x["score"], reverse=True)[:top_k]


def _parse_code_list(raw_codes: list[dict]) -> list[MedicalCode]:
    """Validate and normalize LLM-returned code objects."""
    parsed: list[MedicalCode] = []
    for item in raw_codes or []:
        try:
            confidence = float(item.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
            parsed.append(
                MedicalCode(
                    code=str(item.get("code", "")).strip(),
                    description=str(item.get("description", "")).strip(),
                    confidence=confidence,
                    confidence_label=_confidence_label(confidence),
                    supporting_evidence=item.get("supporting_evidence", []),
                )
            )
        except Exception as exc:
            logger.warning(f"Skipping malformed code entry: {item} — {exc}")
    return parsed


class RAGPipeline:
    """
    Orchestrates the full RAG → LLM → structured-output pipeline.
    All PHI is stripped before any data leaves this class.
    """

    def __init__(self) -> None:
        self._anonymizer = get_anonymizer()
        self._vector_store = get_vector_store()
        self._groq = get_groq_service()

    async def process(
        self,
        clinical_text: str,
        session_id: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Full pipeline: anonymize → retrieve → generate → validate.
        Returns a dict compatible with CodingResponse schema.
        """
        t_start = time.perf_counter()

        # ── Step 1: PHI Anonymization ─────────────────────────────────────────
        anon_result: AnonymizationResult = self._anonymizer.anonymize(clinical_text)
        safe_text = anon_result.anonymized_text
        logger.info(
            f"[{session_id}] PHI entities removed: {anon_result.entities_removed}"
        )

        # ── Step 2: Dual Retrieval (ICD-10 + CPT) ────────────────────────────
        # Extract focused clinical queries instead of embedding the full note.
        # A long note produces a blurry average vector; short targeted queries
        # retrieve far more relevant codes.
        top_k_retrieval = settings.rag_top_k
        clinical_queries = _extract_clinical_queries(safe_text)
        logger.debug(f"[{session_id}] Clinical queries: {clinical_queries}")

        # Run each query and merge results, keeping the highest score per code
        icd_results = _multi_query_search(
            self._vector_store.search_icd10, clinical_queries, top_k=top_k_retrieval
        )
        cpt_results = _multi_query_search(
            self._vector_store.search_cpt, clinical_queries, top_k=top_k_retrieval
        )
        logger.debug(
            f"[{session_id}] Retrieved {len(icd_results)} ICD-10, {len(cpt_results)} CPT candidates"
        )

        # ── Step 3: Build RAG Context ─────────────────────────────────────────
        rag_context = _build_rag_context(icd_results, cpt_results)

        # ── Step 4: LLM Code Extraction ───────────────────────────────────────
        llm_output = await self._groq.extract_medical_codes(
            clinical_text=safe_text,
            rag_context=rag_context,
            top_k=top_k,
        )

        # ── Step 5: Parse & Validate ──────────────────────────────────────────
        icd10_codes = _parse_code_list(llm_output.get("icd10_codes", []))
        cpt_codes = _parse_code_list(llm_output.get("cpt_codes", []))

        elapsed_ms = int((time.perf_counter() - t_start) * 1000)

        return {
            "session_id": session_id,
            "anonymized_text": safe_text,
            "original_hash": anon_result.original_hash,
            "phi_found": anon_result.phi_found,
            "entities_removed": anon_result.entities_removed,
            "clinical_summary": llm_output.get("clinical_summary", ""),
            "icd10_codes": icd10_codes,
            "cpt_codes": cpt_codes,
            "explanation": llm_output.get("explanation", ""),
            "retrieval_count": len(icd_results) + len(cpt_results),
            "processing_time_ms": elapsed_ms,
            "avg_icd_confidence": (
                sum(c.confidence for c in icd10_codes) / len(icd10_codes)
                if icd10_codes else 0.0
            ),
            "avg_cpt_confidence": (
                sum(c.confidence for c in cpt_codes) / len(cpt_codes)
                if cpt_codes else 0.0
            ),
        }


_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
