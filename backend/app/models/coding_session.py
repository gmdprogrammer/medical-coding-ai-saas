import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.database import Base


class CodingSession(Base):
    __tablename__ = "coding_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Input (anonymized — PHI stripped before storage)
    original_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    anonymized_text: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured output stored as JSON
    icd10_codes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cpt_codes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quality metrics
    avg_icd_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_cpt_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_count: Mapped[int] = mapped_column(Integer, default=0)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Feedback loop
    feedback_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    feedback_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(50), default="pending")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", lazy="selectin")


class CodeFeedback(Base):
    __tablename__ = "code_feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("coding_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    code_type: Mapped[str] = mapped_column(String(10), nullable=False)  # icd10 | cpt
    suggested_code: Mapped[str] = mapped_column(String(20), nullable=False)
    correct_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    was_correct: Mapped[bool | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
