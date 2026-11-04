"""
FastAPI authentication and authorization dependencies for NEXUS AI.
"""
from typing import List, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.schemas.user import UserRole, UserPrincipal
from app.services.firebase_service import verify_firebase_id_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserPrincipal:
    """
    Authenticate user via Firebase ID Token Bearer header.
    Rejects missing or invalid tokens with HTTP 401.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_firebase_id_token(credentials.credentials)


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserPrincipal]:
    """
    Optional authentication for endpoints readable by both public community and authenticated users.
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        return verify_firebase_id_token(credentials.credentials)
    except HTTPException:
        return None


def require_role(allowed_roles: List[UserRole]):
    """
    Role-Based Access Control (RBAC) dependency factory.
    Enforces verified role claims on protected operations with HTTP 403.
    """
    def role_checker(
        current_user: UserPrincipal = Depends(get_current_user)
    ) -> UserPrincipal:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {[r.value for r in allowed_roles]}. Current role: {current_user.role.value}",
            )
        return current_user

    return role_checker
