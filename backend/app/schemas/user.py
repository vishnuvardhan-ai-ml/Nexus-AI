"""
Pydantic schemas for User identity, roles, and profiles.
"""
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    COMMUNITY_USER = "COMMUNITY_USER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


class UserProfile(BaseModel):
    uid: str = Field(..., description="Firebase unique user ID")
    email: str = Field(..., max_length=254, description="User verified email address")
    display_name: Optional[str] = Field(default=None, description="Full or preferred civic display name")
    role: UserRole = Field(default=UserRole.COMMUNITY_USER, description="Verified RBAC role")
    created_at: str = Field(..., description="Account creation timestamp (ISO 8601)")
    updated_at: Optional[str] = Field(default=None, description="Profile update timestamp (ISO 8601)")


class UserPrincipal(BaseModel):
    """Internal user context extracted from verified Firebase ID token."""
    uid: str
    email: str
    role: UserRole = UserRole.COMMUNITY_USER
    claims: Dict[str, Any] = Field(default_factory=dict)


class ProfileSyncRequest(BaseModel):
    """Payload sent by client immediately following registration to record user doc."""
    display_name: Optional[str] = Field(default=None, max_length=100)
