"""
HIPAA-aligned audit logging.
Every medical decision, data access, and auth event is recorded
immutably in the audit_logs table with full context.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.audit_log import AuditLog


class AuditLogger:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def log(
        self,
        action: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
        outcome: str = "success",
        error_message: str | None = None,
    ) -> None:
        entry = AuditLog(
            user_id=user_id,
            session_id=session_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_metadata=metadata,
            outcome=outcome,
            error_message=error_message,
        )
        try:
            self._db.add(entry)
            await self._db.flush()
        except Exception as exc:
            # Audit logging must never crash the main request
            logger.error(f"Audit log write failed: {exc}")

    async def log_coding_request(
        self,
        user_id: str,
        session_id: str,
        ip_address: str | None,
        phi_found: bool,
    ) -> None:
        await self.log(
            action="CODING_REQUEST",
            user_id=user_id,
            session_id=session_id,
            resource_type="coding_session",
            resource_id=session_id,
            ip_address=ip_address,
            metadata={"phi_detected": phi_found},
        )

    async def log_auth_event(
        self,
        action: str,
        user_id: str | None,
        ip_address: str | None,
        outcome: str = "success",
        error: str | None = None,
    ) -> None:
        await self.log(
            action=action,
            user_id=user_id,
            ip_address=ip_address,
            outcome=outcome,
            error_message=error,
        )
