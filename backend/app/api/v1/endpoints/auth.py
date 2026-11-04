"""
Authentication and role inspection endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.schemas.user import UserPrincipal, UserProfile, ProfileSyncRequest
from app.api.deps import get_current_user
from app.services.incident_service import sync_user_profile

router = APIRouter()


@router.get(
    "/me",
    response_model=UserPrincipal,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Identity & Role",
    description="Returns verified user identity and trusted RBAC role claims.",
)
@rate_limit(settings.RATE_LIMIT_AUTH)
def get_me(
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> UserPrincipal:
    """Return the authenticated caller's identity and verified role."""
    return current_user


@router.post(
    "/sync-profile",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Sync User Profile Document",
    description="Initializes or updates the user profile record in Firestore. Strictly enforces COMMUNITY_USER on initial creation.",
)
@rate_limit(settings.RATE_LIMIT_AUTH)
def sync_profile(
    sync_data: ProfileSyncRequest,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> UserProfile:
    """Synchronize user profile to database."""
    return sync_user_profile(sync_data, current_user)
