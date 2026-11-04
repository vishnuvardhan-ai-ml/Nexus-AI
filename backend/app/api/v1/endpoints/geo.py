"""
FastAPI Geospatial Intelligence Endpoints.

Routes:
- GET /api/v1/geo/incidents : GeoJSON RFC 7946 FeatureCollection with spatial bounding-box & privacy filters.
- GET /api/v1/geo/summary   : Geospatial health metrics, geocoding coverage, and unplotted incident statistics.
- GET /api/v1/geo/clusters  : Exploratory spatial grid clustering for dense civic incident concentrations.
"""
from typing import Optional, List, Annotated
from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from app.core.config import settings
from app.core.rate_limit import rate_limit

from app.schemas.incident import IncidentCategory, IncidentSeverity, IncidentStatus
from app.schemas.risk import RiskLevel
from app.schemas.user import UserPrincipal
from app.schemas.geo import (
    BoundingBox,
    GeoIncidentCollectionResponse,
    GeoSummaryResponse,
    GeoClusterItem,
)
from app.api.deps import get_current_user
from app.services.geo_service import (
    get_geo_incidents,
    get_geo_summary_metrics,
    compute_exploratory_clusters,
)

router = APIRouter()


@router.get(
    "/incidents",
    response_model=GeoIncidentCollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Geospatial Incidents (GeoJSON RFC 7946)",
    description=(
        "Retrieves verified community incidents as a GeoJSON FeatureCollection. "
        "Strictly enforces WGS84 coordinate ordering as [longitude, latitude]. "
        "Performs server-side bounding-box filtering and authoritative assessment joining without "
        "ever fabricating risk scores for unassessed records. "
        "Sanitizes reporter emails and applies privacy coordinate generalization (~1km) for non-owner community viewers. "
        "Tracks and returns unplotted incident reports lacking usable coordinates."
    ),
)
@rate_limit(settings.RATE_LIMIT_GEO)
def get_geospatial_incidents(
    category: Annotated[Optional[IncidentCategory], Query(description="Filter by hazard category")] = None,
    risk_level: Annotated[Optional[RiskLevel], Query(description="Filter by assessed risk tier")] = None,
    incident_status: Annotated[Optional[IncidentStatus], Query(alias="status", description="Filter by status")] = None,
    min_lat: Annotated[Optional[float], Query(ge=-90.0, le=90.0, description="Bounding box minimum latitude")] = None,
    min_lng: Annotated[Optional[float], Query(ge=-180.0, le=180.0, description="Bounding box minimum longitude")] = None,
    max_lat: Annotated[Optional[float], Query(ge=-90.0, le=90.0, description="Bounding box maximum latitude")] = None,
    max_lng: Annotated[Optional[float], Query(ge=-180.0, le=180.0, description="Bounding box maximum longitude")] = None,
    only_own: Annotated[bool, Query(description="Restricts records strictly to current user's submissions")] = False,
    limit: Annotated[int, Query(ge=1, le=500, description="Bounded batch query limit (default 100, max 500)")] = 100,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> GeoIncidentCollectionResponse:
    """
    Retrieve community incidents in GeoJSON format.
    Requires verified Firebase Authentication.
    """
    bbox: Optional[BoundingBox] = None
    bbox_params = [min_lat, min_lng, max_lat, max_lng]
    
    if any(p is not None for p in bbox_params):
        if not all(p is not None for p in bbox_params):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All four bounding box parameters (min_lat, min_lng, max_lat, max_lng) must be provided together.",
            )
        try:
            bbox = BoundingBox(
                min_lat=min_lat,
                min_lng=min_lng,
                max_lat=max_lat,
                max_lng=max_lng,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    return get_geo_incidents(
        current_user=current_user,
        category=category.value if category else None,
        risk_level=risk_level.value if risk_level else None,
        status_filter=incident_status.value if incident_status else None,
        bbox=bbox,
        only_own=only_own,
        limit=limit,
    )


@router.get(
    "/summary",
    response_model=GeoSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Geospatial Coverage & Health Summary",
    description=(
        "Returns aggregate metrics on geographic data completeness: total recorded incidents, "
        "geocoded vs. unplotted incident counts, spatial coverage percentage, active counts, "
        "and distribution across authoritative risk tiers."
    ),
)
@rate_limit(settings.RATE_LIMIT_GEO)
def get_geospatial_summary(
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> GeoSummaryResponse:
    """Return high-level geospatial metrics and completeness statistics."""
    return get_geo_summary_metrics(current_user=current_user)


@router.get(
    "/clusters",
    response_model=List[GeoClusterItem],
    status_code=status.HTTP_200_OK,
    summary="Get Exploratory Spatial Clusters",
    description=(
        "Computes spatial grid clusters for multi-incident concentrations. "
        "Mandatory disclosure: Grid clusters and density metrics are explicitly labeled exploratory "
        "and do not assert continuous citywide hazard coverage."
    ),
)
@rate_limit(settings.RATE_LIMIT_GEO)
def get_geospatial_clusters(
    category: Annotated[Optional[IncidentCategory], Query(description="Filter clusters by category")] = None,
    grid_size: Annotated[float, Query(ge=0.005, le=0.5, description="Spatial grid cell size in degrees")] = 0.02,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> List[GeoClusterItem]:
    """Return exploratory spatial clusters."""
    return compute_exploratory_clusters(
        current_user=current_user,
        category=category.value if category else None,
        grid_size_degrees=grid_size,
    )
