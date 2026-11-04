"""
Comprehensive Unit and Integration Tests for Milestone 4, Stage 1 & 2:
Geospatial Intelligence, GeoJSON (RFC 7946), Bounding Boxes, and Privacy Controls.

Test Coverage:
1. Coordinate Range & WGS84 Validation:
   - Valid coordinates in range [-90, 90] and [-180, 180].
   - Invalid latitude (>90, <-90) and longitude (>180, <-180) rejected.
   - Non-numeric, NaN, and Infinite coordinate handling.
   - Valid (0.0, 0.0) Null Island coordinates accepted (not universally rejected).
2. GeoJSON RFC 7946 Compliance & Coordinate Order:
   - Strict [longitude, latitude] ordering in Point geometry.
   - FeatureCollection structure with total_matched, geocoded_count, unplotted_count.
   - Bounding box calculation [min_lng, min_lat, max_lng, max_lat].
3. Unplotted Incident Tracking:
   - Records with missing or malformed coordinates tracked in unplotted_items with reason.
   - Zero silent data loss.
4. Risk Assessment Joining (Mandatory Rule #1):
   - Never infers risk score from severity when unassessed.
   - Unassessed incidents return risk_score=None, risk_level=None, assessment_status="NOT_ASSESSED".
   - Latest assessment selection when multiple assessments exist for an incident.
5. Role-Based Privacy & Precision Sanitization:
   - reporter_email and reporter_uid stripped from GeoJSON properties for all roles.
   - Community users viewing their own incident get precision="EXACT".
   - Community users viewing another citizen's incident get precision="GENERALIZED" (~1km).
   - Admins and Analysts get precision="EXACT" across all incidents.
6. Bounding-Box Spatial Filtering:
   - Incidents outside bbox excluded from features.
   - Incomplete bounding box parameters rejected with 400 Bad Request.
   - min_lat > max_lat or min_lng > max_lng rejected.
7. Geospatial Summary & Telemetry:
   - Coverage percentage calculation.
   - Active incident count and risk level distribution.
8. Exploratory Spatial Grid Clustering:
   - Centroid calculation and exploratory disclosure tag.
9. Authentication & Route Registration:
   - 401 Unauthorized when credentials are missing.
   - OpenAPI router verification for /api/v1/geo/incidents, /api/v1/geo/summary, /api/v1/geo/clusters.
"""
import math
from typing import Dict, Any, Optional, List
import pytest
from pydantic import ValidationError
from fastapi import HTTPException, status

from app.schemas.incident import IncidentCategory, IncidentSeverity, IncidentStatus
from app.schemas.risk import RiskLevel
from app.schemas.user import UserPrincipal, UserRole
from app.schemas.geo import (
    CoordinatePrecision,
    AssessmentStatus,
    GeoPointGeometry,
    BoundingBox,
    GeoIncidentCollectionResponse,
    GeoSummaryResponse,
    GeoClusterItem,
)
from app.services.geo_service import (
    validate_wgs84_coordinates,
    is_point_in_bbox,
    sanitize_coordinate_precision,
    get_geo_incidents,
    get_geo_summary_metrics,
    compute_exploratory_clusters,
)
from app.api.v1.endpoints.geo import (
    get_geospatial_incidents,
    get_geospatial_summary,
    get_geospatial_clusters,
)
from app.services.firebase_service import set_firestore_client_for_testing
from app.main import app
from app.api.deps import get_current_user


# ==============================================================================
# MOCK FIRESTORE FOR DETERMINISTIC, ISOLATED OFFLINE TESTING
# ==============================================================================

class MockDocSnapshot:
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]]):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> Dict[str, Any]:
        return self._data.copy() if self._data else {}


class MockDocRef:
    def __init__(self, doc_id: str, store: Dict[str, Any]):
        self.id = doc_id
        self._store = store

    def set(self, data: Dict[str, Any]):
        self._store[self.id] = data.copy() if isinstance(data, dict) else data

    def get(self) -> MockDocSnapshot:
        return MockDocSnapshot(self.id, self._store.get(self.id))


class MockQuery:
    def __init__(self, collection_name: str, items: Dict[str, Any]):
        self.collection_name = collection_name
        self._items = items
        self._filters = []
        self._limit_val = None

    def where(self, *args, **kwargs):
        # Support both where(field, op, val) and where(filter=FieldFilter(...))
        field_name = None
        target_val = None
        if "filter" in kwargs:
            ff = kwargs["filter"]
            field_name = getattr(ff, "field_path", None) or getattr(ff, "_field_path", None)
            target_val = getattr(ff, "value", None) or getattr(ff, "_value", None)
        elif len(args) == 3:
            field_name = args[0]
            target_val = args[2]

        new_q = MockQuery(self.collection_name, self._items.copy())
        new_q._filters = list(self._filters)
        if field_name:
            new_q._filters.append((field_name, target_val))
        new_q._limit_val = self._limit_val
        return new_q

    def limit(self, count: int):
        new_q = MockQuery(self.collection_name, self._items.copy())
        new_q._filters = list(self._filters)
        new_q._limit_val = count
        return new_q

    def stream(self):
        matched = []
        for doc_id, doc_data in self._items.items():
            passes = True
            for f_name, f_val in self._filters:
                if doc_data.get(f_name) != f_val:
                    passes = False
                    break
            if passes:
                matched.append(MockDocSnapshot(doc_id, doc_data))
        if self._limit_val:
            matched = matched[:self._limit_val]
        return matched


class MockCollection:
    def __init__(self, name: str, parent_db: "MockFirestore"):
        self.name = name
        self._parent = parent_db

    def document(self, doc_id: str) -> MockDocRef:
        store = self._parent._collections.setdefault(self.name, {})
        return MockDocRef(doc_id, store)

    def stream(self):
        store = self._parent._collections.setdefault(self.name, {})
        return [MockDocSnapshot(doc_id, data) for doc_id, data in store.items()]

    def limit(self, count: int) -> MockQuery:
        store = self._parent._collections.setdefault(self.name, {})
        return MockQuery(self.name, store).limit(count)

    def where(self, *args, **kwargs) -> MockQuery:
        store = self._parent._collections.setdefault(self.name, {})
        return MockQuery(self.name, store).where(*args, **kwargs)


class MockFirestore:
    def __init__(self):
        self._collections: Dict[str, Dict[str, Any]] = {}

    def collection(self, name: str) -> MockCollection:
        return MockCollection(name, self)


@pytest.fixture(autouse=True)
def setup_mock_firestore():
    """Inject fresh isolated mock Firestore store for each test."""
    mock_db = MockFirestore()
    set_firestore_client_for_testing(mock_db)
    yield mock_db
    set_firestore_client_for_testing(None)


# Test Principals
COMMUNITY_USER_A = UserPrincipal(
    uid="user_citizen_123",
    email="citizen.one@example.com",
    role=UserRole.COMMUNITY_USER,
)
COMMUNITY_USER_B = UserPrincipal(
    uid="user_citizen_456",
    email="citizen.two@example.com",
    role=UserRole.COMMUNITY_USER,
)
ANALYST_USER = UserPrincipal(
    uid="user_analyst_789",
    email="analyst@nexus.gov",
    role=UserRole.ANALYST,
)
ADMIN_USER = UserPrincipal(
    uid="user_admin_999",
    email="admin@nexus.gov",
    role=UserRole.ADMIN,
)


# ==============================================================================
# 1. COORDINATE RANGE & WGS84 VALIDATION TESTS
# ==============================================================================

def test_validate_wgs84_valid_coordinates():
    """Verify that standard global coordinates parse correctly."""
    valid, lat, lng, reason = validate_wgs84_coordinates(12.9716, 77.5946)
    assert valid is True
    assert lat == 12.9716
    assert lng == 77.5946
    assert reason == "VALID"


def test_validate_wgs84_null_island_accepted():
    """
    Mandatory Rule #3:
    Do not universally reject valid (0, 0) coordinates.
    Null Island (0.0, 0.0) is mathematically valid WGS84.
    """
    valid, lat, lng, reason = validate_wgs84_coordinates(0.0, 0.0)
    assert valid is True
    assert lat == 0.0
    assert lng == 0.0
    assert reason == "VALID"


def test_validate_wgs84_out_of_bounds_rejection():
    """Verify that latitude > 90 / < -90 and longitude > 180 / < -180 are rejected."""
    # Latitude out of bounds
    valid, _, _, reason = validate_wgs84_coordinates(91.0, 77.5)
    assert valid is False
    assert "LATITUDE_OUT_OF_BOUNDS" in reason

    valid, _, _, reason = validate_wgs84_coordinates(-90.1, 77.5)
    assert valid is False
    assert "LATITUDE_OUT_OF_BOUNDS" in reason

    # Longitude out of bounds
    valid, _, _, reason = validate_wgs84_coordinates(12.9, 180.1)
    assert valid is False
    assert "LONGITUDE_OUT_OF_BOUNDS" in reason

    valid, _, _, reason = validate_wgs84_coordinates(12.9, -180.5)
    assert valid is False
    assert "LONGITUDE_OUT_OF_BOUNDS" in reason


def test_validate_wgs84_missing_or_non_numeric():
    """Verify that None, strings without numbers, NaN, and Inf are handled cleanly."""
    valid, _, _, reason = validate_wgs84_coordinates(None, 77.5)
    assert valid is False
    assert reason == "MISSING_COORDINATES"

    valid, _, _, reason = validate_wgs84_coordinates(12.9, None)
    assert valid is False
    assert reason == "MISSING_COORDINATES"

    valid, _, _, reason = validate_wgs84_coordinates("not_a_num", 77.5)
    assert valid is False
    assert reason == "INVALID_COORDINATE_FORMAT"

    valid, _, _, reason = validate_wgs84_coordinates(float("nan"), 77.5)
    assert valid is False
    assert reason == "NON_FINITE_COORDINATES"

    valid, _, _, reason = validate_wgs84_coordinates(12.9, float("inf"))
    assert valid is False
    assert reason == "NON_FINITE_COORDINATES"


# ==============================================================================
# 2. GEOJSON RFC 7946 SCHEMA & COORDINATE ORDERING TESTS
# ==============================================================================

def test_geojson_point_geometry_coordinate_order():
    """
    Mandatory Rule #6:
    GeoJSON RFC 7946 strictly requires [longitude, latitude] ordering.
    """
    geom = GeoPointGeometry(coordinates=[77.5946, 12.9716])
    assert geom.type == "Point"
    assert geom.coordinates[0] == 77.5946  # Longitude first
    assert geom.coordinates[1] == 12.9716  # Latitude second

    # Reject invalid length
    with pytest.raises(ValidationError):
        GeoPointGeometry(coordinates=[77.5946])

    with pytest.raises(ValidationError):
        GeoPointGeometry(coordinates=[77.5946, 12.9716, 100.0])

    # Reject out of bounds in schema
    with pytest.raises(ValidationError):
        GeoPointGeometry(coordinates=[185.0, 12.0])


# ==============================================================================
# 3. BOUNDING BOX SCHEMA & FILTERING TESTS
# ==============================================================================

def test_bounding_box_validation():
    """Verify bounding box validation logic."""
    bbox = BoundingBox(min_lat=12.0, min_lng=77.0, max_lat=13.0, max_lng=78.0)
    assert bbox.min_lat == 12.0
    assert bbox.max_lat == 13.0

    # min_lat > max_lat rejected
    with pytest.raises(ValidationError):
        BoundingBox(min_lat=13.5, min_lng=77.0, max_lat=13.0, max_lng=78.0)

    # min_lng > max_lng rejected
    with pytest.raises(ValidationError):
        BoundingBox(min_lat=12.0, min_lng=79.0, max_lat=13.0, max_lng=78.0)


def test_is_point_in_bbox():
    """Verify point containment inside bounding box."""
    bbox = BoundingBox(min_lat=10.0, min_lng=20.0, max_lat=30.0, max_lng=40.0)
    assert is_point_in_bbox(20.0, 30.0, bbox) is True
    assert is_point_in_bbox(9.9, 30.0, bbox) is False
    assert is_point_in_bbox(30.1, 30.0, bbox) is False
    assert is_point_in_bbox(20.0, 19.9, bbox) is False
    assert is_point_in_bbox(20.0, 40.1, bbox) is False
    assert is_point_in_bbox(20.0, 30.0, None) is True


# ==============================================================================
# 4. GET /api/v1/geo/incidents - FULL ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_geo_incidents_unassessed_record_returns_null_risk(setup_mock_firestore: MockFirestore):
    """
    Mandatory Rule #1:
    Never generate or infer a risk score from incident severity when no saved
    risk assessment exists. Return null risk_score and risk_level with NOT_ASSESSED status.
    """
    db = setup_mock_firestore
    db.collection("incidents").document("inc_unassessed_1").set({
        "id": "inc_unassessed_1",
        "title": "Severe Flooding Near Metro",
        "description": "Water level reaching 2 feet across road.",
        "category": "waterlogging",
        "severity": "HIGH",  # Notice HIGH severity
        "status": "reported",
        "location": "MG Road Station",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "reporter_uid": "user_citizen_123",
        "created_at": "2026-11-04T08:00:00Z",
    })

    # Call endpoint directly with analyst principal
    res = get_geospatial_incidents(
        category=None,
        risk_level=None,
        incident_status=None,
        current_user=ANALYST_USER,
    )

    assert res.type == "FeatureCollection"
    assert len(res.features) == 1
    feat = res.features[0]

    # Verify geometry
    assert feat.geometry.type == "Point"
    assert feat.geometry.coordinates == [77.5946, 12.9716]  # [lng, lat]

    # Verify properties
    props = feat.properties
    assert props.id == "inc_unassessed_1"
    assert props.severity == IncidentSeverity.HIGH
    assert props.assessment_status == AssessmentStatus.NOT_ASSESSED
    assert props.risk_score is None  # Strictly None! Not inferred from HIGH
    assert props.risk_level is None  # Strictly None!
    assert props.assessment_id is None


def test_geo_incidents_joins_latest_saved_assessment(setup_mock_firestore: MockFirestore):
    """
    Mandatory Rule #8:
    Join the latest valid saved assessment for each incident.
    """
    db = setup_mock_firestore
    db.collection("incidents").document("inc_assessed_1").set({
        "id": "inc_assessed_1",
        "title": "Exposed Power Transformer Wire",
        "description": "Sparks visible in rain.",
        "category": "electrical_hazard",
        "severity": "HIGH",
        "status": "investigating",
        "location": "Indiranagar 100ft Road",
        "latitude": 12.9784,
        "longitude": 77.6408,
        "reporter_uid": "user_citizen_123",
        "created_at": "2026-11-04T07:00:00Z",
    })

    # Older assessment
    db.collection("risk_assessments").document("assess_old").set({
        "id": "assess_old",
        "incident_id": "inc_assessed_1",
        "risk_score": 65.0,
        "risk_level": "HIGH",
        "primary_driver": "Hazard Severity",
        "assessed_at": "2026-11-04T07:15:00Z",
    })

    # Newer assessment
    db.collection("risk_assessments").document("assess_latest").set({
        "id": "assess_latest",
        "incident_id": "inc_assessed_1",
        "risk_score": 82.5,
        "risk_level": "HIGH",
        "primary_driver": "Exposure",
        "assessed_at": "2026-11-04T07:45:00Z",
    })

    res = get_geospatial_incidents(current_user=ANALYST_USER)
    assert len(res.features) == 1
    props = res.features[0].properties

    assert props.assessment_status == AssessmentStatus.ASSESSED
    assert props.risk_score == 82.5
    assert props.risk_level == RiskLevel.HIGH
    assert props.assessment_id == "assess_latest"
    assert props.primary_driver == "Exposure"
    assert props.assessed_at == "2026-11-04T07:45:00Z"


def test_geo_incidents_unplotted_incident_tracking(setup_mock_firestore: MockFirestore):
    """
    Mandatory Rule #7:
    Provide unplotted incident counts for records without usable coordinates,
    without silently discarding them.
    """
    db = setup_mock_firestore
    # 1. Incident with valid coordinates
    db.collection("incidents").document("inc_valid").set({
        "id": "inc_valid",
        "title": "Valid Incident",
        "category": "road_damage",
        "severity": "LOW",
        "status": "reported",
        "location": "Ring Road",
        "latitude": 12.9123,
        "longitude": 77.6543,
        "reporter_uid": "user_citizen_123",
        "created_at": "2026-11-04T08:00:00Z",
    })

    # 2. Incident with missing coordinates (None)
    db.collection("incidents").document("inc_no_gps").set({
        "id": "inc_no_gps",
        "title": "Pothole Outside Gate",
        "category": "road_damage",
        "severity": "MEDIUM",
        "status": "reported",
        "location": "Near Landmark Without GPS",
        "latitude": None,
        "longitude": None,
        "reporter_uid": "user_citizen_123",
        "created_at": "2026-11-04T08:10:00Z",
    })

    # 3. Incident with out of bounds coordinates
    db.collection("incidents").document("inc_bad_coords").set({
        "id": "inc_bad_coords",
        "title": "Malformed Point",
        "category": "waste_management",
        "severity": "LOW",
        "status": "reported",
        "location": "Typo in GPS",
        "latitude": 120.0,  # Invalid
        "longitude": 77.0,
        "reporter_uid": "user_citizen_123",
        "created_at": "2026-11-04T08:20:00Z",
    })

    res = get_geospatial_incidents(current_user=ANALYST_USER)

    assert res.total_matched == 3
    assert res.geocoded_count == 1
    assert res.unplotted_count == 2
    assert len(res.features) == 1
    assert len(res.unplotted_items) == 2

    # Check unplotted reasons
    unplotted_reasons = {item.id: item.reason for item in res.unplotted_items}
    assert unplotted_reasons["inc_no_gps"] == "MISSING_COORDINATES"
    assert "LATITUDE_OUT_OF_BOUNDS" in unplotted_reasons["inc_bad_coords"]


def test_geo_incidents_privacy_and_precision_sanitization(setup_mock_firestore: MockFirestore):
    """
    Mandatory Rule #2 & #9:
    - reporter_email, reporter_uid stripped.
    - Community users viewing their own incident get precision="EXACT".
    - Community users viewing another citizen's incident get precision="GENERALIZED".
    - Analysts and Admins get precision="EXACT" across all records.
    """
    db = setup_mock_firestore
    # Incident submitted by Citizen A (precise coordinates: 12.971612, 77.594634)
    db.collection("incidents").document("inc_citizen_a").set({
        "id": "inc_citizen_a",
        "title": "Citizen A Incident",
        "category": "waterlogging",
        "severity": "MEDIUM",
        "status": "reported",
        "location": "123 Private Lane",
        "latitude": 12.971612,
        "longitude": 77.594634,
        "reporter_uid": COMMUNITY_USER_A.uid,
        "reporter_email": "private.citizen.a@personal.com",
        "created_at": "2026-11-04T08:00:00Z",
    })

    # Case 1: Citizen A viewing their own incident -> EXACT precision
    res_a = get_geospatial_incidents(current_user=COMMUNITY_USER_A)
    assert len(res_a.features) == 1
    feat_a = res_a.features[0]
    assert feat_a.properties.is_own_incident is True
    assert feat_a.properties.precision == CoordinatePrecision.EXACT
    assert feat_a.geometry.coordinates == [77.594634, 12.971612]
    # Ensure reporter email is NOT exposed
    assert not hasattr(feat_a.properties, "reporter_email")
    assert not hasattr(feat_a.properties, "reporter_uid")

    # Case 2: Citizen B viewing Citizen A's incident -> GENERALIZED precision (~1km)
    res_b = get_geospatial_incidents(current_user=COMMUNITY_USER_B)
    assert len(res_b.features) == 1
    feat_b = res_b.features[0]
    assert feat_b.properties.is_own_incident is False
    assert feat_b.properties.precision == CoordinatePrecision.GENERALIZED
    # Coordinates rounded to 2 decimal places: 12.97, 77.59
    assert feat_b.geometry.coordinates == [77.59, 12.97]

    # Case 3: Analyst viewing Citizen A's incident -> EXACT precision
    res_analyst = get_geospatial_incidents(current_user=ANALYST_USER)
    feat_analyst = res_analyst.features[0]
    assert feat_analyst.properties.precision == CoordinatePrecision.EXACT
    assert feat_analyst.geometry.coordinates == [77.594634, 12.971612]


def test_geo_incidents_bounding_box_filtering(setup_mock_firestore: MockFirestore):
    """Verify that bounding box filters exclude out-of-viewport incidents."""
    db = setup_mock_firestore
    # Point 1: Inside Bangalore Central (lat=12.97, lng=77.59)
    db.collection("incidents").document("inc_blr").set({
        "id": "inc_blr",
        "title": "Bangalore Incident",
        "category": "waterlogging",
        "severity": "LOW",
        "status": "reported",
        "location": "Central Bangalore",
        "latitude": 12.97,
        "longitude": 77.59,
        "reporter_uid": "user_citizen_123",
        "created_at": "2026-11-04T08:00:00Z",
    })

    # Point 2: Delhi (lat=28.61, lng=77.20)
    db.collection("incidents").document("inc_delhi").set({
        "id": "inc_delhi",
        "title": "Delhi Incident",
        "category": "extreme_heat",
        "severity": "HIGH",
        "status": "reported",
        "location": "Connaught Place",
        "latitude": 28.61,
        "longitude": 77.20,
        "reporter_uid": "user_citizen_123",
        "created_at": "2026-11-04T08:00:00Z",
    })

    # Query with Bangalore bounding box
    res = get_geospatial_incidents(
        min_lat=12.8,
        min_lng=77.4,
        max_lat=13.1,
        max_lng=77.8,
        current_user=ANALYST_USER,
    )

    assert len(res.features) == 1
    assert res.features[0].properties.id == "inc_blr"


def test_geo_incidents_incomplete_bbox_rejected():
    """Verify that providing partial bbox parameters returns 400 Bad Request."""
    with pytest.raises(HTTPException) as exc:
        get_geospatial_incidents(
            min_lat=12.0,
            min_lng=77.0,
            max_lat=None,  # Missing max_lat
            max_lng=78.0,
            current_user=ANALYST_USER,
        )
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "All four bounding box parameters" in exc.value.detail


# ==============================================================================
# 5. GET /api/v1/geo/summary - GEOSPATIAL METRICS TESTS
# ==============================================================================

def test_get_geospatial_summary_metrics(setup_mock_firestore: MockFirestore):
    """Verify calculation of coverage percentage, risk breakdown, and active count."""
    db = setup_mock_firestore
    # 2 geocoded, 1 unplotted
    db.collection("incidents").document("inc_1").set({
        "id": "inc_1",
        "category": "waterlogging",
        "status": "reported",
        "latitude": 12.97,
        "longitude": 77.59,
    })
    db.collection("incidents").document("inc_2").set({
        "id": "inc_2",
        "category": "road_damage",
        "status": "mitigating",
        "latitude": 12.98,
        "longitude": 77.60,
    })
    db.collection("incidents").document("inc_3").set({
        "id": "inc_3",
        "category": "waste_management",
        "status": "resolved",
        "latitude": None,
        "longitude": None,
    })

    # Assessment for inc_1
    db.collection("risk_assessments").document("assess_1").set({
        "id": "assess_1",
        "incident_id": "inc_1",
        "risk_level": "HIGH",
    })

    summary = get_geospatial_summary(current_user=ANALYST_USER)

    assert summary.total_incidents == 3
    assert summary.geocoded_count == 2
    assert summary.unplotted_count == 1
    assert summary.coverage_percentage == 66.7
    assert summary.high_risk_count == 1
    assert summary.not_assessed_count == 2
    assert summary.active_incidents_count == 2  # reported + mitigating


# ==============================================================================
# 6. GET /api/v1/geo/clusters - EXPLORATORY SPATIAL CLUSTERING
# ==============================================================================

def test_get_geospatial_clusters_exploratory_disclosure(setup_mock_firestore: MockFirestore):
    """
    Mandatory Rule #4:
    Clustering must be explicitly labeled exploratory and require sufficient verified records.
    """
    db = setup_mock_firestore
    for idx in range(4):
        db.collection("incidents").document(f"inc_clust_{idx}").set({
            "id": f"inc_clust_{idx}",
            "title": f"Incident {idx}",
            "category": "waterlogging",
            "severity": "MEDIUM",
            "status": "reported",
            "location": "North Zone",
            "latitude": 13.01 + (idx * 0.002),
            "longitude": 77.55 + (idx * 0.002),
            "reporter_uid": "user_citizen_123",
            "created_at": "2026-11-04T08:00:00Z",
        })

    clusters = get_geospatial_clusters(current_user=ANALYST_USER)
    assert len(clusters) >= 1
    first_cluster = clusters[0]
    assert first_cluster.count == 4
    assert first_cluster.is_exploratory is True
    assert len(first_cluster.centroid) == 2  # [lng, lat]


# ==============================================================================
# 7. AUTHENTICATION & ROUTE REGISTRATION VERIFICATION
# ==============================================================================

def test_geo_endpoints_authentication_enforcement():
    """Verify that unauthenticated calls without token raise 401."""
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=None)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_geo_router_registration():
    """Verify that all three /api/v1/geo endpoints are mounted in the FastAPI app."""
    openapi_paths = app.openapi()["paths"]
    assert "/api/v1/geo/incidents" in openapi_paths
    assert "get" in openapi_paths["/api/v1/geo/incidents"]

    assert "/api/v1/geo/summary" in openapi_paths
    assert "get" in openapi_paths["/api/v1/geo/summary"]

    assert "/api/v1/geo/clusters" in openapi_paths
    assert "get" in openapi_paths["/api/v1/geo/clusters"]
