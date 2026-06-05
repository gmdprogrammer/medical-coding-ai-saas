from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone
from collections import Counter

from app.models.database import get_db
from app.models.user import User
from app.models.coding_session import CodingSession
from app.models.audit_log import AuditLog
from app.dependencies import require_admin
from app.schemas.admin import AdminUserUpdate, AdminSessionReview, DashboardStats, AuditLogEntry
from app.core.audit_logger import AuditLogger

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_sessions = (await db.execute(select(func.count()).select_from(CodingSession))).scalar_one()
    sessions_today = (
        await db.execute(
            select(func.count()).select_from(CodingSession).where(
                CodingSession.created_at >= today_start
            )
        )
    ).scalar_one()
    pending_reviews = (
        await db.execute(
            select(func.count()).select_from(CodingSession).where(
                CodingSession.review_status == "pending"
            )
        )
    ).scalar_one()

    avg_icd = (
        await db.execute(select(func.avg(CodingSession.avg_icd_confidence)))
    ).scalar_one() or 0.0
    avg_cpt = (
        await db.execute(select(func.avg(CodingSession.avg_cpt_confidence)))
    ).scalar_one() or 0.0

    # Feedback-based accuracy rate
    total_with_feedback = (
        await db.execute(
            select(func.count()).select_from(CodingSession).where(
                CodingSession.feedback_rating.is_not(None)
            )
        )
    ).scalar_one()
    high_rated = (
        await db.execute(
            select(func.count()).select_from(CodingSession).where(
                CodingSession.feedback_rating >= 4
            )
        )
    ).scalar_one()
    accuracy_rate = (high_rated / total_with_feedback) if total_with_feedback else 0.0

    # Top codes — tally from recent 200 sessions
    recent_sessions_result = await db.execute(
        select(CodingSession.icd10_codes, CodingSession.cpt_codes)
        .order_by(desc(CodingSession.created_at))
        .limit(200)
    )
    recent_rows = recent_sessions_result.all()

    icd_counter: Counter = Counter()
    cpt_counter: Counter = Counter()
    for row in recent_rows:
        for code in (row.icd10_codes or []):
            if isinstance(code, dict) and code.get("code"):
                icd_counter[code["code"]] += 1
        for code in (row.cpt_codes or []):
            if isinstance(code, dict) and code.get("code"):
                cpt_counter[code["code"]] += 1

    top_icd10 = [{"code": c, "count": n} for c, n in icd_counter.most_common(10)]
    top_cpt = [{"code": c, "count": n} for c, n in cpt_counter.most_common(10)]

    return DashboardStats(
        total_users=total_users,
        total_sessions=total_sessions,
        sessions_today=sessions_today,
        avg_confidence=round((avg_icd + avg_cpt) / 2, 3),
        pending_reviews=pending_reviews,
        top_icd10_codes=top_icd10,
        top_cpt_codes=top_cpt,
        accuracy_rate=round(accuracy_rate, 3),
    )


@router.get("/users")
async def list_users(
    page: int = 1,
    per_page: int = 20,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    rows = (
        await db.execute(
            select(User).order_by(desc(User.created_at)).offset(offset).limit(per_page)
        )
    ).scalars().all()
    return {
        "users": [
            {
                "id": u.id, "email": u.email, "full_name": u.full_name,
                "role": u.role, "is_active": u.is_active, "is_verified": u.is_verified,
                "created_at": u.created_at.isoformat(),
            }
            for u in rows
        ],
        "total": total,
        "page": page,
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    body: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_verified is not None:
        user.is_verified = body.is_verified

    auditor = AuditLogger(db)
    await auditor.log(
        "ADMIN_USER_UPDATE", user_id=admin.id,
        resource_type="user", resource_id=user_id,
        metadata=body.model_dump(exclude_none=True),
    )
    await db.commit()
    return {"status": "updated", "user_id": user_id}


@router.get("/sessions/pending")
async def pending_sessions(
    page: int = 1,
    per_page: int = 20,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    stmt = (
        select(CodingSession)
        .where(CodingSession.review_status == "pending")
        .order_by(desc(CodingSession.created_at))
        .offset(offset)
        .limit(per_page)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": s.id, "clinical_summary": s.clinical_summary,
            "avg_icd_confidence": s.avg_icd_confidence,
            "avg_cpt_confidence": s.avg_cpt_confidence,
            "created_at": s.created_at.isoformat(),
        }
        for s in rows
    ]


@router.patch("/sessions/{session_id}/review")
async def review_session(
    session_id: str,
    body: AdminSessionReview,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CodingSession).where(CodingSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.review_status = body.review_status
    session.reviewed_by = admin.id
    if body.reviewer_notes:
        session.reviewer_notes = body.reviewer_notes

    auditor = AuditLogger(db)
    await auditor.log(
        "SESSION_REVIEWED", user_id=admin.id,
        session_id=session_id,
        metadata={"status": body.review_status, "notes": body.reviewer_notes},
    )
    await db.commit()
    return {"status": "reviewed", "session_id": session_id}


@router.get("/audit-logs", response_model=list[AuditLogEntry])
async def get_audit_logs(
    page: int = 1,
    per_page: int = 50,
    action: str | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).offset(offset).limit(per_page)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = (await db.execute(stmt)).scalars().all()
    return rows
