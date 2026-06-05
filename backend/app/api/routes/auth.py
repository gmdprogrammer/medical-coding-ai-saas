from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db
from app.models.user import User
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    create_verification_token, create_reset_token,
)
from app.core.audit_logger import AuditLogger
from app.schemas.auth import (
    UserRegister, UserLogin, TokenResponse, UserResponse,
    RefreshTokenRequest, PasswordChangeRequest,
    ForgotPasswordRequest, ResetPasswordRequest, VerifyEmailRequest,
    UserProfileUpdateRequest,
)
from app.dependencies import get_current_user
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        organization=body.organization,
    )
    db.add(user)
    await db.flush()

    auditor = AuditLogger(db)
    await auditor.log_auth_event(
        "USER_REGISTERED", user.id, request.client.host if request.client else None
    )
    await db.commit()
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    auditor = AuditLogger(db)
    ip = request.client.host if request.client else None

    if not user or not verify_password(body.password, user.hashed_password):
        await auditor.log_auth_event("LOGIN_FAILED", None, ip, outcome="failure")
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    user.last_login = datetime.now(timezone.utc)
    await auditor.log_auth_event("LOGIN_SUCCESS", user.id, ip)
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UserProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user.full_name = body.full_name
    user.organization = body.organization
    await db.commit()
    return user


@router.put("/change-password", status_code=200)
async def change_password(
    body: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    user.hashed_password = hash_password(body.new_password)
    auditor = AuditLogger(db)
    await auditor.log("PASSWORD_CHANGED", user_id=user.id)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.post("/forgot-password", status_code=200)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    
    if user:
        token = create_reset_token(user.id)
        # Log simulated email containing the token link
        print(f"\n[EMAIL SIMULATION] Password reset request for {user.email}.\nLink: http://localhost:3000/auth/reset-password?token={token}\n")
        auditor = AuditLogger(db)
        await auditor.log_auth_event("PASSWORD_RESET_REQUESTED", user.id, None)
        await db.commit()
        
    return {"message": "If the email is registered, a password reset link has been sent."}


@router.post("/reset-password", status_code=200)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
    if payload.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Invalid token type")
        
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="User not found or inactive")
        
    user.hashed_password = hash_password(body.new_password)
    auditor = AuditLogger(db)
    await auditor.log_auth_event("PASSWORD_RESET_SUCCESS", user.id, None)
    await db.commit()
    return {"message": "Password has been reset successfully."}


@router.post("/verify-email/request", status_code=200)
async def request_email_verification(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.is_verified:
        return {"message": "Email is already verified."}
        
    token = create_verification_token(user.id)
    # Log simulated verification email containing the token link
    print(f"\n[EMAIL SIMULATION] Email verification request for {user.email}.\nLink: http://localhost:3000/auth/verify-email?token={token}\n")
    
    auditor = AuditLogger(db)
    await auditor.log_auth_event("EMAIL_VERIFICATION_REQUESTED", user.id, None)
    await db.commit()
    return {"message": "Verification email has been sent."}


@router.post("/verify-email", status_code=200)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
    if payload.get("type") != "verification":
        raise HTTPException(status_code=400, detail="Invalid token type")
        
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="User not found or inactive")
        
    if user.is_verified:
        return {"message": "Email is already verified."}
        
    user.is_verified = True
    auditor = AuditLogger(db)
    await auditor.log_auth_event("EMAIL_VERIFIED_SUCCESS", user.id, None)
    await db.commit()
    return {"message": "Email verified successfully."}

