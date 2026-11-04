"""
Geospatial Intelligence Service Layer.
Handles WGS84 coordinate validation, GeoJSON RFC 7946 generation,
server-side bounding box filtering, authoritative assessment joining,
and role-based privacy sanitization.
"""
import logging
import math
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status

from app.schemas.incident import IncidentCategory, IncidentSeverity, IncidentStatus
from app.schemas.risk import RiskLevel
from app.schemas.user import UserPrincipal, UserRole
from app.schemas.geo import (
    CoordinatePrecision,
    AssessmentStatus,
    GeoPointGeometry,
    GeoIncidentProperties,
    GeoIncidentFeature,
    UnplottedIncidentSummary,
    BoundingBox,
    GeoIncidentCollectionResponse,
    GeoSummaryResponse,
    GeoClusterItem,
)
from app.services.firebase_service import get_firestore_client

logger = logging.getLogger("nexus.services.geo")

# Coordinate rounding constants for privacy
GENERALIZED_DECIMAL_PLACES = 2  # ~1.1 km precision (protects residential addresses)
EXACT_DECIMAL_PLACES = 6        # ~0.1 m precision (for municipal field operations)


def validate_wgs84_coordinates(lat: Any, lng: Any) -> Tuple[bool, Optional[float], Optional[float], str]:
    """
    Validate coordinates against WGS84 specifications.
    
    Returns:
        (is_valid, parsed_lat, parsed_lng, reason_if_invalid)
        
    Policy:
    - Rejects None, NaN, and Infinite values.
    - Rejects values outside WGS84 ranges: latitude in [-90.0, 90.0], longitude in [-180.0, 180.0].
    - Does NOT universally reject (0.0, 0.0) as Null Island is mathematically valid,
      unless coordinates are missing or fail numeric conversion.
    """
    if lat is None or lng is None:
        return False, None, None, "MISSING_COORDINATES"

    try:
        f_lat = float(lat)
        f_lng = float(lng)
    except (ValueError, TypeError):
        return False, None, None, "INVALID_COORDINATE_FORMAT"

    if math.isnan(f_lat) or math.isnan(f_lng) or math.isinf(f_lat) or math.isinf(f_lng):
        return False, None, None, "NON_FINITE_COORDINATES"

    if not (-90.0 <= f_lat <= 90.0):
        return False, None, None, f"LATITUDE_OUT_OF_BOUNDS: {f_lat} not in [-90.0, 90.0]"

    if not (-180.0 <= f_lng <= 180.0):
        return False, None, None, f"LONGITUDE_OUT_OF_BOUNDS: {f_lng} not in [-180.0, 180.0]"

    return True, f_lat, f_lng, "VALID"


def is_point_in_bbox(lat: float, lng: float, bbox: Optional[BoundingBox]) -> bool:
    """Check if a coordinate point falls inside the given bounding box."""
    if bbox is None:
        return True
    return (
        bbox.min_lat <= lat <= bbox.max_lat
        and bbox.min_lng <= lng <= bbox.max_lng
    )


def sanitize_coordinate_precision(
    lat: float,
    lng: float,
    is_owner: bool,
    user_role: UserRole,
) -> Tuple[float, float, CoordinatePrecision]:
    """
    Apply role-based geographic privacy sanitization.
    
    - Admins and Analysts receive exact coordinates.
    - The incident owner receives exact coordinates for their own submissions.
    - Other citizens (Community Users) receive generalized coordinates (~1km)
      to avoid revealing private residential locations.
    """
    if user_role in (UserRole.ADMIN, UserRole.ANALYST) or is_owner:
        return round(lat, EXACT_DECIMAL_PLACES), round(lng, EXACT_DECIMAL_PLACES), CoordinatePrecision.EXACT
    
    return round(lat, GENERALIZED_DECIMAL_PLACES), round(lng, GENERALIZED_DECIMAL_PLACES), CoordinatePrecision.GENERALIZED


def _fetch_latest_assessments_map(db: Any, incident_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch the latest valid risk assessment for a collection of incident IDs from Firestore.
    Returns mapping: {incident_id: assessment_dict}.
    Never infers risk scores for unassessed incidents.
    """
    assessments_map: Dict[str, Dict[str, Any]] = {}
    if not incident_ids:
        return assessments_map

    try:
        # Stream assessments collection
        # If incident_ids is small or mock environment, stream collection and index by incident_id
        assess_docs = list(db.collection("risk_assessments").stream())
        for doc in assess_docs:
            data = doc.to_dict()
            if not data:
                continue
            inc_id = data.get("incident_id")
            if inc_id and inc_id in incident_ids:
                # Compare timestamp to keep strictly the latest assessment
                existing = assessments_map.get(inc_id)
                current_time = data.get("assessed_at") or data.get("created_at") or ""
                existing_time = (existing.get("assessed_at") or existing.get("created_at") or "") if existing else ""
                
                if not existing or current_time >= existing_time:
                    assessments_map[inc_id] = data
    except Exception as exc:
        logger.warning(f"Could not load risk assessments for geo mapping: {exc}")

    return assessments_map


def get_geo_incidents(
    current_user: UserPrincipal,
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    status_filter: Optional[str] = None,
    bbox: Optional[BoundingBox] = None,
    only_own: bool = False,
    limit: int = 100,
) -> GeoIncidentCollectionResponse:
    """
    Retrieve community incidents in GeoJSON RFC 7946 format with spatial filtering,
    authoritative assessment joining, and privacy redaction.
    
    Firestore Query Strategy & Limitations:
    Cloud Firestore does not support multi-field inequality queries (e.g. lat >= min_lat AND lng >= min_lng)
    without composite indexes. Hence, the strategy is:
    1. Apply equality/in filters (status, category) where possible.
    2. Retrieve a bounded window of records ordered by recency (up to `limit`).
    3. Filter coordinates server-side against the bounding box.
    4. Categorize unplotted records rather than discarding them.
    5. Join latest authoritative risk assessments without fabricating missing scores.
    """
    db = get_firestore_client()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloud Firestore client is unavailable. Cannot retrieve geospatial data.",
        )

    # 1. Base query with bounded limit
    query = db.collection("incidents")

    # Native category or status filter if applicable
    if category:
        try:
            from google.cloud.firestore_v1 import FieldFilter
            query = query.where(filter=FieldFilter("category", "==", category))
        except Exception:
            query = query.where("category", "==", category)

    if status_filter:
        try:
            from google.cloud.firestore_v1 import FieldFilter
            query = query.where(filter=FieldFilter("status", "==", status_filter))
        except Exception:
            query = query.where("status", "==", status_filter)

    # Community user restriction if only_own is requested
    if only_own and current_user.role == UserRole.COMMUNITY_USER:
        try:
            from google.cloud.firestore_v1 import FieldFilter
            query = query.where(filter=FieldFilter("reporter_uid", "==", current_user.uid))
        except Exception:
            query = query.where("reporter_uid", "==", current_user.uid)

    # Retrieve docs with bounded scan limit
    safe_limit = max(1, min(limit, 500))
    try:
        docs = list(query.limit(safe_limit).stream())
        raw_items: List[Dict[str, Any]] = [d.to_dict() for d in docs if d.to_dict()]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firestore incident geospatial query failed: {exc}",
        ) from exc

    has_more = len(raw_items) >= safe_limit

    # 2. Join latest saved risk assessments
    incident_ids = [item.get("id") for item in raw_items if item.get("id")]
    assessments_map = _fetch_latest_assessments_map(db, incident_ids)

    # 3. Process, validate, filter, and sanitize items
    features: List[GeoIncidentFeature] = []
    unplotted_items: List[UnplottedIncidentSummary] = []
    
    all_lats: List[float] = []
    all_lngs: List[float] = []

    for item in raw_items:
        inc_id = item.get("id", "")
        item_reporter = item.get("reporter_uid") or item.get("reported_by") or ""
        is_owner = (item_reporter == current_user.uid)

        # Match risk_level filter if specified
        assessment_data = assessments_map.get(inc_id)
        saved_risk_level = assessment_data.get("risk_level") if assessment_data else None

        if risk_level:
            # If user filtered by a specific risk level, unassessed records or non-matching records do not pass
            if not saved_risk_level or saved_risk_level != risk_level:
                continue

        # Extract incident fields safely
        title = item.get("title", "Untitled Incident")
        try:
            inc_cat = IncidentCategory(item.get("category", "waterlogging"))
        except ValueError:
            inc_cat = IncidentCategory.WATERLOGGING

        try:
            inc_sev = IncidentSeverity(item.get("severity", "MEDIUM"))
        except ValueError:
            inc_sev = IncidentSeverity.MEDIUM

        try:
            inc_stat = IncidentStatus(item.get("status", "reported"))
        except ValueError:
            inc_stat = IncidentStatus.REPORTED

        loc_name = item.get("location", "Unspecified Location")
        created_at = item.get("created_at", "")

        # Assess risk join attributes
        if assessment_data:
            assess_status = AssessmentStatus.ASSESSED
            risk_score = float(assessment_data.get("risk_score", 0.0))
            try:
                r_level = RiskLevel(assessment_data.get("risk_level", "MEDIUM"))
            except ValueError:
                r_level = RiskLevel.MEDIUM
            assessment_id = assessment_data.get("id")
            assessed_at = assessment_data.get("assessed_at") or assessment_data.get("created_at")
            primary_driver = (
                assessment_data.get("primary_driver")
                or assessment_data.get("contributions", {}).get("primary_driver")
            )
        else:
            # Mandatory rule: Never infer or invent risk score from severity
            assess_status = AssessmentStatus.NOT_ASSESSED
            risk_score = None
            r_level = None
            assessment_id = None
            assessed_at = None
            primary_driver = None

        # Coordinate validation
        raw_lat = item.get("latitude")
        raw_lng = item.get("longitude")
        is_valid, valid_lat, valid_lng, reason = validate_wgs84_coordinates(raw_lat, raw_lng)

        if not is_valid:
            # Record cannot be plotted on the map; retain in unplotted items
            unplotted_items.append(
                UnplottedIncidentSummary(
                    id=inc_id,
                    title=title,
                    category=inc_cat,
                    severity=inc_sev,
                    status=inc_stat,
                    location_name=loc_name,
                    created_at=created_at,
                    assessment_status=assess_status,
                    risk_score=risk_score,
                    risk_level=r_level,
                    reason=reason,
                )
            )
            continue

        # Bounding box spatial filter
        if bbox is not None and not is_point_in_bbox(valid_lat, valid_lng, bbox):
            # Outside viewport bounding box
            continue

        # Privacy sanitization
        final_lat, final_lng, precision_level = sanitize_coordinate_precision(
            lat=valid_lat,
            lng=valid_lng,
            is_owner=is_owner,
            user_role=current_user.role,
        )

        all_lats.append(final_lat)
        all_lngs.append(final_lng)

        properties = GeoIncidentProperties(
            id=inc_id,
            title=title,
            category=inc_cat,
            severity=inc_sev,
            status=inc_stat,
            location_name=loc_name,
            created_at=created_at,
            assessment_status=assess_status,
            risk_score=risk_score,
            risk_level=r_level,
            assessment_id=assessment_id,
            assessed_at=assessed_at,
            primary_driver=primary_driver,
            precision=precision_level,
            is_own_incident=is_owner,
        )

        # RFC 7946 strictly requires [longitude, latitude]
        geometry = GeoPointGeometry(
            type="Point",
            coordinates=[final_lng, final_lat],
        )

        features.append(
            GeoIncidentFeature(
                type="Feature",
                id=inc_id,
                geometry=geometry,
                properties=properties,
            )
        )

    # 4. Compute bounding box and geometric center of plotted features
    calculated_bbox: Optional[List[float]] = None
    center_coords: Optional[List[float]] = None

    if all_lats and all_lngs:
        min_lat = min(all_lats)
        max_lat = max(all_lats)
        min_lng = min(all_lngs)
        max_lng = max(all_lngs)
        # RFC 7946 bbox: [min_lng, min_lat, max_lng, max_lat]
        calculated_bbox = [round(min_lng, 6), round(min_lat, 6), round(max_lng, 6), round(max_lat, 6)]
        center_coords = [
            round(sum(all_lngs) / len(all_lngs), 6),
            round(sum(all_lats) / len(all_lats), 6),
        ]

    total_matched = len(features) + len(unplotted_items)

    return GeoIncidentCollectionResponse(
        type="FeatureCollection",
        features=features,
        total_matched=total_matched,
        geocoded_count=len(features),
        unplotted_count=len(unplotted_items),
        unplotted_items=unplotted_items,
        bbox=calculated_bbox,
        center_coordinates=center_coords,
        limit_applied=safe_limit,
        has_more=has_more,
    )


def get_geo_summary_metrics(current_user: UserPrincipal) -> GeoSummaryResponse:
    """
    Calculate high-level geographic coverage, assessment rates, and risk distribution
    for the geographic workspace header.
    """
    db = get_firestore_client()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloud Firestore client is unavailable.",
        )

    try:
        inc_docs = list(db.collection("incidents").stream())
        all_incidents = [d.to_dict() for d in inc_docs if d.to_dict()]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firestore incident query failed: {exc}",
        ) from exc

    total = len(all_incidents)
    if total == 0:
        return GeoSummaryResponse(
            total_incidents=0,
            geocoded_count=0,
            unplotted_count=0,
            coverage_percentage=0.0,
            high_risk_count=0,
            medium_risk_count=0,
            low_risk_count=0,
            not_assessed_count=0,
            category_distribution={},
            active_incidents_count=0,
        )

    # Count coordinates
    geocoded = 0
    unplotted = 0
    active_count = 0
    cat_counts: Dict[str, int] = {}

    incident_ids: List[str] = []
    for inc in all_incidents:
        inc_id = inc.get("id")
        if inc_id:
            incident_ids.append(inc_id)

        cat = inc.get("category", "other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

        if inc.get("status") in ["reported", "investigating", "mitigating"]:
            active_count += 1

        is_valid, _, _, _ = validate_wgs84_coordinates(inc.get("latitude"), inc.get("longitude"))
        if is_valid:
            geocoded += 1
        else:
            unplotted += 1

    coverage_pct = round((geocoded / total) * 100, 1) if total > 0 else 0.0

    # Fetch assessment distribution
    assessments_map = _fetch_latest_assessments_map(db, incident_ids)
    high_count = 0
    medium_count = 0
    low_count = 0
    not_assessed = 0

    for inc_id in incident_ids:
        assess = assessments_map.get(inc_id)
        if not assess:
            not_assessed += 1
        else:
            lvl = assess.get("risk_level")
            if lvl == "HIGH":
                high_count += 1
            elif lvl == "MEDIUM":
                medium_count += 1
            elif lvl == "LOW":
                low_count += 1
            else:
                not_assessed += 1

    return GeoSummaryResponse(
        total_incidents=total,
        geocoded_count=geocoded,
        unplotted_count=unplotted,
        coverage_percentage=coverage_pct,
        high_risk_count=high_count,
        medium_risk_count=medium_count,
        low_risk_count=low_count,
        not_assessed_count=not_assessed,
        category_distribution=cat_counts,
        active_incidents_count=active_count,
    )


def compute_exploratory_clusters(
    current_user: UserPrincipal,
    category: Optional[str] = None,
    grid_size_degrees: float = 0.02,  # ~2.2 km grid cell
) -> List[GeoClusterItem]:
    """
    Compute exploratory spatial grid clusters.
    Mandatory Integrity Requirement:
    Clustering is clearly marked exploratory and requires sufficient verified nearby records.
    Does not assert real-world geographic continuity.
    """
    geo_data = get_geo_incidents(
        current_user=current_user,
        category=category,
        limit=500,
    )

    if not geo_data.features:
        return []

    # Grid hashing
    grid: Dict[Tuple[int, int], List[GeoIncidentFeature]] = {}
    for feat in geo_data.features:
        lng, lat = feat.geometry.coordinates[0], feat.geometry.coordinates[1]
        grid_x = int(math.floor(lng / grid_size_degrees))
        grid_y = int(math.floor(lat / grid_size_degrees))
        grid.setdefault((grid_x, grid_y), []).append(feat)

    clusters: List[GeoClusterItem] = []
    for (gx, gy), items in grid.items():
        count = len(items)
        if count == 0:
            continue

        lats = [it.geometry.coordinates[1] for it in items]
        lngs = [it.geometry.coordinates[0] for it in items]
        centroid = [round(sum(lngs) / count, 6), round(sum(lats) / count, 6)]

        high_count = sum(1 for it in items if it.properties.risk_level == RiskLevel.HIGH)
        med_count = sum(1 for it in items if it.properties.risk_level == RiskLevel.MEDIUM)
        low_count = sum(1 for it in items if it.properties.risk_level == RiskLevel.LOW)
        unassessed = sum(1 for it in items if it.properties.assessment_status == AssessmentStatus.NOT_ASSESSED)

        cat_counts: Dict[str, int] = {}
        for it in items:
            c = it.properties.category.value
            cat_counts[c] = cat_counts.get(c, 0) + 1
        dom_cat = max(cat_counts, key=cat_counts.get) if cat_counts else None

        clusters.append(
            GeoClusterItem(
                cluster_id=f"cluster_{gx}_{gy}",
                centroid=centroid,
                count=count,
                high_risk_count=high_count,
                medium_risk_count=med_count,
                low_risk_count=low_count,
                not_assessed_count=unassessed,
                dominant_category=dom_cat,
                is_exploratory=True,
            )
        )

    # Sort descending by count
    return sorted(clusters, key=lambda c: c.count, reverse=True)
