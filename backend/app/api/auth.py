from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User, UserStatus
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login", response_model=TokenResponse, summary="Obtain a JWT access token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate with email + password (using OAuth2 form format).

    Returns a JWT containing:
        user_id, hospital_id, role

    This token must be sent as `Authorization: Bearer <token>` on all protected endpoints.
    """
    # 1. Find user (OAuth2 uses 'username' field for the email)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # 2. Verify password
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # 3. Check user status
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active.",
        )

    # 4. Generate token with tenant context embedded
    token_data = {
        "user_id": str(user.id),
        "hospital_id": str(user.hospital_id) if user.hospital_id else None,
        "role": user.role.value,
    }
    access_token = create_access_token(token_data)

    return TokenResponse(access_token=access_token, token_type="bearer")
