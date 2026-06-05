from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.coding_service import CodingService
from app.schemas.coding import (
    CodingRequest, CodingResponse, FeedbackRequest, SessionListResponse,
)

router = APIRouter(prefix="/coding", tags=["Medical Coding"])


@router.post("/analyze", response_model=CodingResponse, status_code=201)
async def analyze_clinical_text(
    body: CodingRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Core endpoint. Accepts clinical text and returns structured ICD-10 + CPT codes.
    PHI is automatically stripped before any AI processing.
    """
    svc = CodingService(db)
    ip = request.client.host if request.client else None
    return await svc.process_clinical_text(body, user, ip_address=ip)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    page: int = 1,
    per_page: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of the authenticated user's coding sessions."""
    svc = CodingService(db)
    return await svc.get_user_sessions(user, page=page, per_page=per_page)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full details of a specific coding session."""
    svc = CodingService(db)
    return await svc.get_session_detail(session_id, user)


@router.post("/feedback", status_code=200)
async def submit_feedback(
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit accuracy rating and code corrections to improve the system."""
    svc = CodingService(db)
    return await svc.submit_feedback(body, user)
