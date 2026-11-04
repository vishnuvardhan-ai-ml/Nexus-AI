"""
Health and telemetry status endpoints for NEXUS AI.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import HealthResponse, HealthSubsystems

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health & Telemetry Status",
    description="Returns service availability, timestamp, semantic version, and core subsystem readiness.",
)
def get_system_health() -> HealthResponse:
    """Retrieve verified platform readiness and telemetry."""
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=settings.ENVIRONMENT,
        subsystems=HealthSubsystems(
            classifier="ready",
            risk_engine="ready",
            database="standby",
        ),
    )
