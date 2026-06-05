"""
Coding Service
━━━━━━━━━━━━━
Orchestration layer between the API route and the RAG pipeline.
Handles persistence, audit logging, and session management.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from fastapi import HTTPException, status
from loguru import logger

from app.models.coding_session import CodingSession, CodeFeedback
from app.models.user import User
from app.services.rag_service import get_rag_pipeline
from app.core.audit_logger import AuditLogger
from app.schemas.coding import CodingRequest, CodingResponse, FeedbackRequest





class CodingService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._pipeline = get_rag_pipeline()
        self._auditor = AuditLogger(db)

    async def process_clinical_text(
        self,
        request: CodingRequest,
        user: User,
        ip_address: str | None = None,
    ) -> CodingResponse:
        session_id = str(uuid.uuid4())

        try:
            result = await self._pipeline.process(
                clinical_text=request.clinical_text,
                session_id=session_id,
                top_k=request.top_k_codes,
            )
        except Exception as exc:
            await self._auditor.log(
                action="CODING_REQUEST",
                user_id=user.id,
                session_id=session_id,
                ip_address=ip_address,
                outcome="failure",
                error_message=str(exc),
            )
            await self._db.commit()
            logger.error(f"RAG pipeline error for session {session_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Medical coding pipeline error. Please try again.",
            )

        # ── Persist session (never store the raw original text — HIPAA) ───────
        icd_list = [c.model_dump() for c in result["icd10_codes"]]
        cpt_list = [c.model_dump() for c in result["cpt_codes"]]

        session = CodingSession(
            id=session_id,
            user_id=user.id,
            original_text_hash=result["original_hash"],
            anonymized_text=result["anonymized_text"],
            clinical_summary=result["clinical_summary"],
            icd10_codes=icd_list,
            cpt_codes=cpt_list,
            explanation=result["explanation"],
            avg_icd_confidence=result["avg_icd_confidence"],
            avg_cpt_confidence=result["avg_cpt_confidence"],
            retrieval_count=result["retrieval_count"],
            processing_time_ms=result["processing_time_ms"],
        )
        self._db.add(session)

        await self._auditor.log_coding_request(
            user_id=user.id,
            session_id=session_id,
            ip_address=ip_address,
            phi_found=result["phi_found"],
        )
        await self._db.commit()

        return CodingResponse(
            session_id=session_id,
            clinical_summary=result["clinical_summary"],
            icd10_codes=result["icd10_codes"],
            cpt_codes=result["cpt_codes"],
            explanation=result["explanation"] if request.include_explanation else "",
            processing_time_ms=result["processing_time_ms"],
            phi_detected=result["phi_found"],
            created_at=datetime.now(timezone.utc),
        )

    async def submit_feedback(
        self,
        request: FeedbackRequest,
        user: User,
    ) -> dict:
        stmt = select(CodingSession).where(
            CodingSession.id == request.session_id,
            CodingSession.user_id == user.id,
        )
        result = await self._db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        session.feedback_rating = request.rating
        session.feedback_notes = request.notes

        if request.code_corrections:
            for correction in request.code_corrections:
                fb = CodeFeedback(
                    session_id=session.id,
                    user_id=user.id,
                    code_type=correction.get("code_type", "unknown"),
                    suggested_code=correction.get("suggested", ""),
                    correct_code=correction.get("correct"),
                    was_correct=correction.get("was_correct"),
                    notes=correction.get("notes"),
                )
                self._db.add(fb)

        await self._auditor.log(
            action="FEEDBACK_SUBMITTED",
            user_id=user.id,
            session_id=session.id,
            metadata={"rating": request.rating},
        )
        await self._db.commit()
        return {"status": "accepted", "session_id": session.id}

    async def get_user_sessions(
        self,
        user: User,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        offset = (page - 1) * per_page
        count_stmt = select(func.count()).select_from(CodingSession).where(
            CodingSession.user_id == user.id
        )
        total = (await self._db.execute(count_stmt)).scalar_one()

        stmt = (
            select(CodingSession)
            .where(CodingSession.user_id == user.id)
            .order_by(desc(CodingSession.created_at))
            .offset(offset)
            .limit(per_page)
        )
        rows = (await self._db.execute(stmt)).scalars().all()

        return {
            "sessions": [
                {
                    "id": s.id,
                    "clinical_summary": s.clinical_summary,
                    "icd10_count": len(s.icd10_codes or []),
                    "cpt_count": len(s.cpt_codes or []),
                    "avg_icd_confidence": s.avg_icd_confidence,
                    "avg_cpt_confidence": s.avg_cpt_confidence,
                    "feedback_rating": s.feedback_rating,
                    "review_status": s.review_status,
                    "created_at": s.created_at.isoformat(),
                }
                for s in rows
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    async def get_session_detail(self, session_id: str, user: User) -> dict:
        stmt = select(CodingSession).where(CodingSession.id == session_id)
        if user.role != "admin":
            stmt = stmt.where(CodingSession.user_id == user.id)
        result = await self._db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await self._auditor.log(
            action="SESSION_VIEWED",
            user_id=user.id,
            session_id=session_id,
            resource_type="coding_session",
            resource_id=session_id,
        )
        await self._db.commit()

        return {
            "id": session.id,
            "clinical_summary": session.clinical_summary,
            "anonymized_text": session.anonymized_text,
            "icd10_codes": session.icd10_codes,
            "cpt_codes": session.cpt_codes,
            "explanation": session.explanation,
            "avg_icd_confidence": session.avg_icd_confidence,
            "avg_cpt_confidence": session.avg_cpt_confidence,
            "processing_time_ms": session.processing_time_ms,
            "feedback_rating": session.feedback_rating,
            "feedback_notes": session.feedback_notes,
            "review_status": session.review_status,
            "created_at": session.created_at.isoformat(),
        }
