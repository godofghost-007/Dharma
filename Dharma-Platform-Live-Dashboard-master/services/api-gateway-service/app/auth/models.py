"""Authentication models."""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """User login request."""
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    """User login response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserInfo"


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class UserInfo(BaseModel):
    """User information for responses."""
    id: int
    username: str
    email: str
    role: str
    full_name: Optional[str] = None
    department: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    last_login: Optional[str] = None


class UserRegistration(BaseModel):
    """User registration request."""
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(admin|supervisor|analyst|viewer)$")
    full_name: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=100)


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class CurrentUser(BaseModel):
    """Current authenticated user."""
    id: int
    username: str
    email: str
    role: str
    permissions: List[str]
    full_name: Optional[str] = None
    department: Optional[str] = None


# Update forward references
LoginResponse.model_rebuild()