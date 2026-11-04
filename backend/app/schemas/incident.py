"""
Pydantic schemas for Incident reporting and retrieval.
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class IncidentCategory(str, Enum):
    WATERLOGGING = "waterlogging"
    ROAD_DAMAGE = "road_damage"
    ELECTRICAL_HAZARD = "electrical_hazard"
    WASTE_MANAGEMENT = "waste_management"
    EXTREME_HEAT = "extreme_heat"


class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class IncidentStatus(str, Enum):
    REPORTED = "reported"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"


class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Concise summary of the civic hazard")
    description: str = Field(..., min_length=10, max_length=2500, description="Detailed observation or impact description")
    category: IncidentCategory = Field(..., description="Hazard taxonomy category")
    severity: IncidentSeverity = Field(..., description="Initial observed severity level")
    location: str = Field(..., min_length=3, max_length=250, description="Textual address, landmark, or intersection")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="WGS84 Longitude")
    image_url: Optional[str] = Field(default=None, description="Optional image data URI or storage URL")

    @field_validator("title", "location", "description")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be only whitespace")
        return stripped


class IncidentResponse(BaseModel):
    id: str = Field(..., description="Server-generated unique incident identifier")
    title: str
    description: str
    category: IncidentCategory
    severity: IncidentSeverity
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    status: IncidentStatus = IncidentStatus.REPORTED
    reporter_uid: str = Field(..., description="Firebase UID of the reporting user")
    reported_by: str = Field(..., description="Alias matching reporter_uid for UI compatibility")
    reporter_email: str = Field(..., description="Email of the reporter")
    created_at: str = Field(..., description="Server-generated ISO 8601 UTC timestamp")
    updated_at: str = Field(..., description="Server-generated ISO 8601 UTC timestamp")


class IncidentListResponse(BaseModel):
    total: int
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=20, description="Items per page")
    total_pages: int = Field(default=1, description="Total available pages")
    items: List[IncidentResponse]


class IncidentStatsResponse(BaseModel):
    total_incidents: int = Field(default=0, description="Total count of recorded incidents")
    active_incidents: int = Field(default=0, description="Incidents in reported/investigating/mitigating status")
    resolved_incidents: int = Field(default=0, description="Incidents marked resolved")
    high_severity_count: int = Field(default=0, description="Incidents with HIGH severity")
    medium_severity_count: int = Field(default=0, description="Incidents with MEDIUM severity")
    low_severity_count: int = Field(default=0, description="Incidents with LOW severity")
    category_counts: dict[str, int] = Field(default_factory=dict, description="Count of incidents per category")
    mean_risk_score: float = Field(default=0.0, description="Average estimated risk score (0.0 if no incidents)")
