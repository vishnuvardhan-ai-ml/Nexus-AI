"""
Incident endpoints for reporting, listing, and inspecting civic hazards.
"""
import math
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, Request, status
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.schemas.incident import (
    IncidentCreate,
    IncidentResponse,
    IncidentListResponse,
    IncidentStatsResponse,
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)
from app.schemas.user import UserPrincipal
from app.api.deps import get_current_user, get_optional_current_user
from app.services.incident_service import create_incident, list_incidents, get_incident_by_id, get_incident_stats

router = APIRouter()


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Community Incident Report",
    description="Accepts validated incident report, assigns server-side ID & timestamp, and binds reporter ownership.",
)
@rate_limit(settings.RATE_LIMIT_INCIDENT_WRITE)
def report_incident(
    incident_in: IncidentCreate,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> IncidentResponse:
    """Ingest a new community incident report under the verified authenticated user."""
    return create_incident(incident_in, current_user)


@router.get(
    "",
    response_model=IncidentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Community Incidents",
    description="Retrieves a paginated list of incident reports with role-based visibility rules.",
)
@rate_limit(settings.RATE_LIMIT_DEFAULT)
def get_incidents(
    category: Annotated[Optional[IncidentCategory], Query(description="Filter by hazard category")] = None,
    severity: Annotated[Optional[IncidentSeverity], Query(description="Filter by severity level")] = None,
    incident_status: Annotated[Optional[IncidentStatus], Query(alias="status", description="Filter by mitigation status")] = None,
    search: Annotated[Optional[str], Query(description="Search keyword for title, location, or ID")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> IncidentListResponse:
    """
    Retrieve community incident stream.
    Community users can access only their own permitted records.
    Analysts and admins are authorized to view all platform records.
    """
    total, items = list_incidents(
        category=category.value if category else None,
        severity=severity.value if severity else None,
        status_filter=incident_status.value if incident_status else None,
        search=search,
        current_user=current_user,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    return IncidentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get(
    "/stats",
    response_model=IncidentStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Incident Aggregation Telemetry",
    description="Retrieves real aggregate incident metrics from Firestore. Requires authentication.",
)
@rate_limit(settings.RATE_LIMIT_DEFAULT)
def get_stats(
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> IncidentStatsResponse:
    """Return real aggregate incident counts, category breakdowns, and mean risk score."""
    return get_incident_stats(current_user=current_user)


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Incident Details",
    description="Retrieves comprehensive details for a specific incident report with ownership authorization.",
)
@rate_limit(settings.RATE_LIMIT_DEFAULT)
def get_incident(
    incident_id: str,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> IncidentResponse:
    """
    Retrieve individual incident report by unique ID.
    Enforces that community users can only access their own submissions.
    """
    return get_incident_by_id(incident_id, current_user=current_user)
