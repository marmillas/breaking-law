"""
Authentication router for the legal platform.

Provides OAuth2 password-login flow with refresh token rotation,
user registration, and global logout.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import get_db_session, get_tenant_session, get_config, get_current_user, UserContext
from breaking_law.infra.models import User as UserORM, LawFirm
from breaking_law.identity.service import AuthService
from breaking_law.identity.security import PasswordHasher
from breaking_law.shared.rls import set_tenant_context
from breaking_law.domain.schemas.identity import (
    TokenResponse,
    RefreshRequest,
    RefreshResponse,
    UserRegister,
    UserOut,
    LawFirmCreate,
    LawFirmOut,
    LogoutRequest,
)
from sqlalchemy import text

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
):
    """
    OAuth2 password login.

    Accepts username (email) and password, returns a JWT access token
    and a refresh token.

    .. note::
       This endpoint sets `app.login_email` so the RLS lookup policy on
       `users` can resolve the email before the tenant context is known.
    """
    cfg = get_config()
    auth_service = AuthService(
        secret_key=cfg.SECRET_KEY,
        algorithm=cfg.ALGORITHM,
        access_token_expire_minutes=cfg.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    # Set lookup parameter for RLS email-based authentication
    if db.bind and getattr(db.bind.dialect, "name", None) == "postgresql":
        await db.execute(
            text("SELECT set_config('app.login_email', :email, true)"),
            {"email": form_data.username},
        )

    result = await db.execute(
        select(UserORM).where(UserORM.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not PasswordHasher.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set tenant context now that the user is resolved
    await set_tenant_context(db, str(user.law_firm_id))

    access_token = auth_service.create_access_token(data={
        "sub": str(user.id),
        "firm_id": str(user.law_firm_id),
        "email": user.email,
        "role": user.role,
        "name": user.full_name,
    })
    refresh_token = await auth_service.create_refresh_token(user.id, user.law_firm_id, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Rotate a refresh token and issue a new access token + refresh token pair.

    If the provided refresh token has already been used (replay attack),
    the entire token family is revoked and the request is rejected.

    .. note::
       This endpoint sets `app.token_hash` so the RLS lookup policy on
       `refresh_tokens` can resolve the token before the tenant context is known.
    """
    cfg = get_config()
    auth_service = AuthService(
        secret_key=cfg.SECRET_KEY,
        algorithm=cfg.ALGORITHM,
        access_token_expire_minutes=cfg.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    # Set lookup parameter for RLS hash-based authentication
    if db.bind and getattr(db.bind.dialect, "name", None) == "postgresql":
        from breaking_law.identity.security import TokenHasher
        await db.execute(
            text("SELECT set_config('app.token_hash', :h, true)"),
            {"h": TokenHasher.hash_token(data.refresh_token)},
        )

    pair = await auth_service.rotate_refresh_token(data.refresh_token, db)
    if pair is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, refresh_token = pair
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: LogoutRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke the provided refresh token (single-device logout)."""
    cfg = get_config()
    auth_service = AuthService(
        secret_key=cfg.SECRET_KEY,
        algorithm=cfg.ALGORITHM,
        access_token_expire_minutes=cfg.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    # Set lookup parameter for RLS hash-based authentication
    if db.bind and getattr(db.bind.dialect, "name", None) == "postgresql":
        from breaking_law.identity.security import TokenHasher
        await db.execute(
            text("SELECT set_config('app.token_hash', :h, true)"),
            {"h": TokenHasher.hash_token(data.refresh_token)},
        )

    revoked = await auth_service.revoke_refresh_token(data.refresh_token, db)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_session),
):
    """Revoke all refresh tokens for the current user (global logout)."""
    cfg = get_config()
    auth_service = AuthService(
        secret_key=cfg.SECRET_KEY,
        algorithm=cfg.ALGORITHM,
        access_token_expire_minutes=cfg.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    await auth_service.revoke_all_refresh_tokens_for_user(current_user.user_id, db)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register a new user.

    NOTE: In production this should be restricted (e.g., owner-only or invite-only).
    """
    # Set tenant context so RLS allows querying the target law firm
    await set_tenant_context(db, str(data.law_firm_id))

    # Verify law firm exists
    firm_result = await db.execute(
        select(LawFirm).where(LawFirm.id == data.law_firm_id)
    )
    if firm_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Law firm not found")

    # Check email uniqueness
    existing = await db.execute(
        select(UserORM).where(UserORM.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = PasswordHasher.hash_password(data.password)
    user = UserORM(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hashed,
        law_firm_id=data.law_firm_id,
        role=data.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
async def me(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_session),
):
    """Return the currently authenticated user's profile."""
    result = await db.execute(
        select(UserORM).where(UserORM.id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/law-firms", response_model=LawFirmOut, status_code=status.HTTP_201_CREATED)
async def create_law_firm(
    data: LawFirmCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new law firm (tenant).

    NOTE: In production this should require admin or owner privileges.
    """
    # Pre-generate UUID so RLS WITH CHECK allows the insert
    firm_id = uuid.uuid4()
    await set_tenant_context(db, str(firm_id))

    firm = LawFirm(
        id=firm_id,
        name=data.name,
        timezone=data.timezone,
    )
    db.add(firm)
    await db.flush()
    await db.refresh(firm)
    return firm
