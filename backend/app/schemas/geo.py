"""
Pydantic schemas for Geospatial Intelligence, GeoJSON (RFC 7946), Bounding Boxes, and Privacy Controls.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
import math

from app.schemas.incident import IncidentCategory, IncidentSeverity, IncidentStatus
from app.schemas.risk import RiskLevel


class CoordinatePrecision(str, Enum):
    """Level of geographic precision exposed in the response."""
    EXACT = "EXACT"
    GENERALIZED = "GENERALIZED"


class AssessmentStatus(str, Enum):
    """Indicates whether an authoritative risk assessment exists."""
    ASSESSED = "ASSESSED"
    NOT_ASSESSED = "NOT_ASSESSED"


class GeoPointGeometry(BaseModel):
    """
    GeoJSON RFC 7946 Point Geometry.
    Mandatory coordinate ordering: [longitude, latitude].
    """
    type: str = Field(default="Point", frozen=True)
    coordinates: List[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="WGS84 coordinate pair in strictly [longitude, latitude] order."
    )

    @field_validator("coordinates")
    @classmethod
    def validate_wgs84_coordinates(cls, v: List[float]) -> List[float]:
        if len(v) != 2:
            raise ValueError("Coordinates must contain exactly [longitude, latitude].")
        lng, lat = v[0], v[1]
        if math.isnan(lng) or math.isinf(lng) or math.isnan(lat) or math.isinf(lat):
            raise ValueError("Coordinates cannot be NaN or Infinite.")
        if not (-180.0 <= lng <= 180.0):
            raise ValueError(f"Longitude {lng} is outside valid WGS84 range [-180.0, 180.0].")
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude {lat} is outside valid WGS84 range [-90.0, 90.0].")
        return [float(lng), float(lat)]


class GeoIncidentProperties(BaseModel):
    """
    Sanitized civic and risk properties attached to a GeoJSON Feature.
    Reporter email and private user identifiers are strictly excluded.
    """
    id: str = Field(..., description="Unique incident identifier")
    title: str = Field(..., description="Incident title")
    category: IncidentCategory = Field(..., description="Civic hazard category")
    severity: IncidentSeverity = Field(..., description="Observed severity baseline")
    status: IncidentStatus = Field(..., description="Incident mitigation status")
    location_name: str = Field(..., description="Textual landmark or address name")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    
    # Authoritative Assessment Join (Null when no saved assessment exists)
    assessment_status: AssessmentStatus = Field(
        default=AssessmentStatus.NOT_ASSESSED,
        description="ASSESSED if a verified risk assessment exists in Firestore; NOT_ASSESSED otherwise."
    )
    risk_score: Optional[float] = Field(
        default=None,
        description="Authoritative deterministic risk score (0-100). Never inferred from severity when unassessed."
    )
    risk_level: Optional[RiskLevel] = Field(
        default=None,
        description="LOW / MEDIUM / HIGH risk tier from saved assessment. None if unassessed."
    )
    assessment_id: Optional[str] = Field(
        default=None,
        description="Firestore document ID of the joined risk assessment."
    )
    assessed_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 UTC timestamp when the assessment was computed."
    )
    primary_driver: Optional[str] = Field(
        default=None,
        description="Primary factor driving the risk score (Hazard, Exposure, Vulnerability, Duration)."
    )
    
    # Privacy & Access Flags
    precision: CoordinatePrecision = Field(
        default=CoordinatePrecision.EXACT,
        description="EXACT for analysts/admins or owner; GENERALIZED (~100m-1km) for public community views."
    )
    is_own_incident: bool = Field(
        default=False,
        description="True if the requesting user authored this incident report."
    )


class GeoIncidentFeature(BaseModel):
    """RFC 7946 GeoJSON Feature representing a mapped civic hazard."""
    type: str = Field(default="Feature", frozen=True)
    id: str = Field(..., description="Feature ID matching incident ID")
    geometry: GeoPointGeometry
    properties: GeoIncidentProperties


class UnplottedIncidentSummary(BaseModel):
    """Summary of an incident report that cannot be placed on the map due to missing coordinates."""
    id: str
    title: str
    category: IncidentCategory
    severity: IncidentSeverity
    status: IncidentStatus
    location_name: str
    created_at: str
    assessment_status: AssessmentStatus = AssessmentStatus.NOT_ASSESSED
    risk_score: Optional[float] = None
    risk_level: Optional[RiskLevel] = None
    reason: str = Field(
        default="NO_COORDINATES_SPECIFIED",
        description="Explanation for why incident is unplotted (e.g., missing coordinates or out of bounds)."
    )


class BoundingBox(BaseModel):
    """Geographic bounding box filter parameters."""
    min_lat: float = Field(..., ge=-90.0, le=90.0, description="Minimum latitude")
    min_lng: float = Field(..., ge=-180.0, le=180.0, description="Minimum longitude")
    max_lat: float = Field(..., ge=-90.0, le=90.0, description="Maximum latitude")
    max_lng: float = Field(..., ge=-180.0, le=180.0, description="Maximum longitude")

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox":
        if self.min_lat > self.max_lat:
            raise ValueError(f"min_lat ({self.min_lat}) cannot be greater than max_lat ({self.max_lat}).")
        if self.min_lng > self.max_lng:
            raise ValueError(f"min_lng ({self.min_lng}) cannot be greater than max_lng ({self.max_lng}).")
        return self


class GeoIncidentCollectionResponse(BaseModel):
    """
    GeoJSON FeatureCollection compliant with RFC 7946, supplemented with
    unplotted incident summaries, counts, and spatial bounds metadata.
    """
    type: str = Field(default="FeatureCollection", frozen=True)
    features: List[GeoIncidentFeature] = Field(default_factory=list)
    total_matched: int = Field(default=0, description="Total incident records matching criteria")
    geocoded_count: int = Field(default=0, description="Number of incidents with valid WGS84 coordinates")
    unplotted_count: int = Field(default=0, description="Number of matching incidents lacking coordinates")
    unplotted_items: List[UnplottedIncidentSummary] = Field(
        default_factory=list,
        description="List of unplotted incident items to display in the UI unplotted drawer."
    )
    bbox: Optional[List[float]] = Field(
        default=None,
        description="RFC 7946 Bounding Box [min_lng, min_lat, max_lng, max_lat] covering all features."
    )
    center_coordinates: Optional[List[float]] = Field(
        default=None,
        description="Calculated geometric center [longitude, latitude] of plotted points."
    )
    limit_applied: int = Field(default=100, description="Maximum items fetched from database query")
    has_more: bool = Field(default=False, description="True if query limit truncated further records")


class GeoSummaryResponse(BaseModel):
    """Aggregated geospatial health and spatial distribution metrics."""
    total_incidents: int = Field(default=0)
    geocoded_count: int = Field(default=0)
    unplotted_count: int = Field(default=0)
    coverage_percentage: float = Field(
        default=0.0,
        description="Percentage of incidents with verified geographic coordinates."
    )
    high_risk_count: int = Field(default=0)
    medium_risk_count: int = Field(default=0)
    low_risk_count: int = Field(default=0)
    not_assessed_count: int = Field(default=0)
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    active_incidents_count: int = Field(default=0)


class GeoClusterItem(BaseModel):
    """
    Spatial aggregation node for grid or radius clustering.
    Density visualisations derived from this schema are explicitly marked exploratory.
    """
    cluster_id: str
    centroid: List[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Centroid coordinate [longitude, latitude]"
    )
    count: int = Field(..., description="Number of incidents in cluster")
    high_risk_count: int = Field(default=0)
    medium_risk_count: int = Field(default=0)
    low_risk_count: int = Field(default=0)
    not_assessed_count: int = Field(default=0)
    dominant_category: Optional[str] = None
    is_exploratory: bool = Field(
        default=True,
        description="Exploratory disclosure: clustering does not assert real-world geographic continuity."
    )
