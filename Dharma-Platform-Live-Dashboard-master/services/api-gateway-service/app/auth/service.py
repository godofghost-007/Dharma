"""Authentication service."""

from typing import Optional
from datetime import datetime
from fastapi import HTTPException, status
import structlog

from ..core.security import security_manager
from ..core.database import db_manager, UserRepository
from .models import LoginResponse, UserInfo, CurrentUser

logger = structlog.get_logger()


class AuthenticationService:
    """Handles user authentication operations."""
    
    def __init__(self):
        self.user_repo = UserRepository(db_manager)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user with username and password."""
        try:
            user = await self.user_repo.get_user_by_username(username)
            if not user:
                logger.warning("Authentication failed: user not found", username=username)
                return None
            
            if not security_manager.verify_password(password, user["hashed_password"]):
                logger.warning("Authentication failed: invalid password", username=username)
                return None
            
            logger.info("User authenticated successfully", username=username)
            return user
            
        except Exception as e:
            logger.error("Authentication error", username=username, error=str(e))
            return None
    
    async def login(self, username: str, password: str) -> LoginResponse:
        """Login user and return tokens."""
        user = await self.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user permissions
        permissions = await self.user_repo.get_user_permissions(user["id"])
        
        # Create token data
        token_data = {
            "sub": user["username"],
            "user_id": user["id"],
            "role": user["role"],
            "permissions": permissions
        }
        
        # Generate tokens
        tokens = security_manager.create_token_pair(token_data)
        
        # Update last login
        await self.user_repo.update_last_login(user["id"])
        
        # Create user info
        user_info = UserInfo(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            full_name=user.get("full_name"),
            department=user.get("department"),
            permissions=permissions,
            last_login=datetime.utcnow().isoformat()
        )
        
        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
            user=user_info
        )
    
    async def refresh_token(self, refresh_token: str) -> LoginResponse:
        """Refresh access token using refresh token."""
        try:
            # Verify refresh token
            token_data = security_manager.verify_token(refresh_token, "refresh")
            
            # Get current user data
            user = await self.user_repo.get_user_by_id(token_data.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Get current permissions
            permissions = await self.user_repo.get_user_permissions(user["id"])
            
            # Create new token data
            new_token_data = {
                "sub": user["username"],
                "user_id": user["id"],
                "role": user["role"],
                "permissions": permissions
            }
            
            # Generate new tokens
            tokens = security_manager.create_token_pair(new_token_data)
            
            # Create user info
            user_info = UserInfo(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                role=user["role"],
                full_name=user.get("full_name"),
                department=user.get("department"),
                permissions=permissions,
                last_login=user.get("last_login").isoformat() if user.get("last_login") else None
            )
            
            return LoginResponse(
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                token_type=tokens.token_type,
                expires_in=tokens.expires_in,
                user=user_info
            )
            
        except Exception as e:
            logger.error("Token refresh error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    
    async def get_current_user(self, token: str) -> CurrentUser:
        """Get current user from access token."""
        token_data = security_manager.verify_token(token, "access")
        
        user = await self.user_repo.get_user_by_id(token_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        permissions = await self.user_repo.get_user_permissions(user["id"])
        
        return CurrentUser(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            permissions=permissions,
            full_name=user.get("full_name"),
            department=user.get("department")
        )
    
    async def register_user(self, user_data: dict) -> UserInfo:
        """Register new user (admin only)."""
        # Hash password
        hashed_password = security_manager.get_password_hash(user_data["password"])
        
        # Prepare user data
        user_record = {
            "username": user_data["username"],
            "email": user_data["email"],
            "hashed_password": hashed_password,
            "role": user_data["role"],
            "full_name": user_data.get("full_name"),
            "department": user_data.get("department"),
            "is_active": True
        }
        
        try:
            user_id = await self.user_repo.create_user(user_record)
            permissions = await self.user_repo.get_user_permissions(user_id)
            
            return UserInfo(
                id=user_id,
                username=user_data["username"],
                email=user_data["email"],
                role=user_data["role"],
                full_name=user_data.get("full_name"),
                department=user_data.get("department"),
                permissions=permissions
            )
            
        except Exception as e:
            logger.error("User registration error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )


# Global authentication service instance
auth_service = AuthenticationService()