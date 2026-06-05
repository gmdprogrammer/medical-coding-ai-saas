"""
Groq API Service
━━━━━━━━━━━━━━━
Wraps the Groq Python client for structured medical code extraction.
Model: llama3-70b-8192 — best balance of accuracy and speed for clinical NLP.

Why Groq?
  • Fastest inference (~500 tok/s vs ~30 tok/s on OpenAI)
  • llama3-70b matches GPT-4 on clinical coding benchmarks
  • Cost-effective for high-volume medical coding SaaS
"""
from __future__ import annotations

import json
import re
from typing import Any

from groq import Groq, APIError, RateLimitError
from loguru import logger

from app.config import get_settings

settings = get_settings()
FALLBACK_GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a certified medical coder (CPC) with expert knowledge of ICD-10-CM, CPT, and HCPCS Level II.

Your task: analyze anonymized clinical text and return the most accurate, specific medical codes.

Coding rules you MUST follow:
1. Code to the HIGHEST specificity — never use an unspecified code when the text supports a more specific one.
   Example: prefer E11.65 (T2DM with hyperglycemia) over E11.9 (T2DM unspecified) when HbA1c or glucose is documented.
2. Only assign codes DIRECTLY SUPPORTED by the clinical text. Do not infer or assume.
3. Sequence ICD-10 codes correctly: primary diagnosis first, then complications, then comorbidities.
4. For procedures, prefer codes from the KNOWLEDGE BASE context over your training memory — the knowledge base is authoritative.
5. Confidence scores must reflect evidence strength:
   - High (≥0.85): explicitly stated in the text with clear clinical documentation
   - Medium (0.65–0.84): implied or partially documented
   - Low (0.50–0.64): possible but not clearly stated — include only if clinically relevant
   - Do NOT include codes with confidence < 0.50
6. Supporting evidence must be direct quotes from the clinical text, not paraphrases.
7. Return ONLY valid JSON — no prose, no markdown, no explanation outside the JSON.
"""

CODING_PROMPT_TEMPLATE = """Analyze the anonymized clinical text below and extract medical codes.

KNOWLEDGE BASE RESULTS (use these as your primary code reference — ranked by relevance):
{rag_context}

CLINICAL TEXT:
{clinical_text}

INSTRUCTIONS:
- Select codes from the knowledge base above when they match the clinical text.
- If a knowledge base code is close but not specific enough, you may use a more specific valid code.
- Do NOT invent codes that are not in the knowledge base unless you are highly confident they are correct.
- Return the top {top_k} most relevant codes per type.

Return ONLY this JSON structure, nothing else:
{{
  "clinical_summary": "2-3 sentence summary of the encounter: chief complaint, key diagnoses, procedures performed",
  "icd10_codes": [
    {{
      "code": "E11.65",
      "description": "Type 2 diabetes mellitus with hyperglycemia",
      "confidence": 0.91,
      "supporting_evidence": ["HbA1c 9.2%", "fasting glucose 210 mg/dL"]
    }}
  ],
  "cpt_codes": [
    {{
      "code": "99213",
      "description": "Office visit, established patient, low-moderate MDM",
      "confidence": 0.85,
      "supporting_evidence": ["referred for medication adjustment"]
    }}
  ],
  "explanation": "Step-by-step coding rationale: why each code was selected, sequencing logic, and any coding guidelines applied"
}}
"""


class GroqService:
    def __init__(self) -> None:
        self._client = Groq(api_key=settings.groq_api_key)

    async def extract_medical_codes(
        self,
        clinical_text: str,
        rag_context: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Send anonymized clinical text + RAG context to Groq LLM.
        Returns structured dict with ICD-10, CPT codes and explanation.
        """
        prompt = CODING_PROMPT_TEMPLATE.format(
            rag_context=rag_context,
            clinical_text=clinical_text,
            top_k=top_k,
        )

        try:
            response = self._client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=settings.groq_max_tokens,
                temperature=settings.groq_temperature,
                # response_format not yet supported on all Groq models; we parse JSON manually
            )
            raw = response.choices[0].message.content
            return self._parse_response(raw)

        except RateLimitError:
            logger.error("Groq rate limit hit — consider increasing plan tier")
            raise
        except APIError as exc:
            err_txt = str(exc)
            if "model_decommissioned" in err_txt or "decommissioned" in err_txt.lower():
                response = self._client.chat.completions.create(
                    model=FALLBACK_GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=settings.groq_max_tokens,
                    temperature=settings.groq_temperature,
                )
                raw = response.choices[0].message.content
                return self._parse_response(raw)
            logger.error(f"Groq API error: {exc}")
            raise

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Extract JSON from LLM response, tolerating markdown fences."""
        # Strip markdown code blocks if present
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find the JSON object within the response
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group())
            logger.error(f"Failed to parse Groq response: {raw[:200]}")
            raise ValueError("Groq returned non-JSON response")

    async def generate_summary(self, clinical_text: str) -> str:
        """Quick summarization call — used for session preview."""
        response = self._client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the clinical encounter in 2-3 sentences. Be concise and clinical.",
                },
                {"role": "user", "content": clinical_text},
            ],
            max_tokens=256,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()


_groq_service: GroqService | None = None


def get_groq_service() -> GroqService:
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqService()
    return _groq_service
