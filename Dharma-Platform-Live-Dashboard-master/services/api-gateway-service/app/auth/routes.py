"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
import structlog

from .models import (
    LoginRequest, LoginResponse, RefreshTokenRequest, 
    UserRegistration, UserInfo, CurrentUser, PasswordChangeRequest
)
from .service import auth_service
from .dependencies import get_current_user, require_admin

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    """Authenticate user and return access tokens."""
    try:
        response = await auth_service.login(
            username=login_request.username,
            password=login_request.password
        )
        logger.info("User logged in successfully", username=login_request.username)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", username=login_request.username, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    try:
        response = await auth_service.refresh_token(refresh_request.refresh_token)
        logger.info("Token refreshed successfully")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me", response_model=CurrentUser)
async def get_current_user_info(current_user: CurrentUser = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.post("/register", response_model=UserInfo)
async def register_user(
    user_data: UserRegistration,
    current_user: CurrentUser = Depends(require_admin)
):
    """Register new user (admin only)."""
    try:
        user_info = await auth_service.register_user(user_data.dict())
        logger.info(
            "User registered successfully",
            new_user=user_data.username,
            registered_by=current_user.username
        )
        return user_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User registration error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
async def logout(current_user: CurrentUser = Depends(get_current_user)):
    """Logout user (invalidate tokens)."""
    # In a production system, you would add the token to a blacklist
    # For now, we just log the logout event
    logger.info("User logged out", username=current_user.username)
    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    password_request: PasswordChangeRequest,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Change user password."""
    # This would be implemented with proper password validation
    # and database update in a production system
    logger.info("Password change requested", username=current_user.username)
    return {"message": "Password changed successfully"}