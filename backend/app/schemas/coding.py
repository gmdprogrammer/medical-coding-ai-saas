from pydantic import BaseModel, Field
from datetime import datetime


class CodingRequest(BaseModel):
    clinical_text: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Clinical notes, procedure descriptions, or diagnosis text",
    )
    include_explanation: bool = True
    top_k_codes: int = Field(default=5, ge=1, le=20)


class MedicalCode(BaseModel):
    code: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_label: str  # High / Medium / Low
    supporting_evidence: list[str] = []


class CodingResponse(BaseModel):
    session_id: str
    clinical_summary: str
    icd10_codes: list[MedicalCode]
    cpt_codes: list[MedicalCode]
    explanation: str
    processing_time_ms: int
    phi_detected: bool
    created_at: datetime


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int = Field(ge=1, le=5, description="Overall rating 1-5")
    notes: str | None = None
    code_corrections: list[dict] | None = None  # [{code_type, suggested, correct}]


class SessionListResponse(BaseModel):
    sessions: list[dict]
    total: int
    page: int
    per_page: int


class AnonymizationReport(BaseModel):
    phi_found: bool
    entities_removed: list[str]
    anonymized_text: str
