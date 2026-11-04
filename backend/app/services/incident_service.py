"""
Business service layer for Incident ingestion, persistence, and querying backed by Cloud Firestore.
Target Project: nexus-ai-4a631
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from app.schemas.incident import (
    IncidentCreate,
    IncidentResponse,
    IncidentStatus,
    IncidentCategory,
    IncidentSeverity,
    IncidentStatsResponse,
)
from app.schemas.user import UserPrincipal, UserProfile, UserRole, ProfileSyncRequest
from app.services.firebase_service import get_firestore_client


def create_incident(incident_in: IncidentCreate, current_user: UserPrincipal) -> IncidentResponse:
    """
    Ingest a new civic incident report into Cloud Firestore collection 'incidents/{incident_id}'.
    Assigns server-generated ID, timestamps, verified reporter UID, and confirms database write.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    incident_id = f"inc_{uuid.uuid4().hex[:12]}"

    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Cloud Firestore client is unavailable. Cannot persist incident.")

    incident_dict: Dict[str, Any] = {
        "id": incident_id,
        "title": incident_in.title,
        "description": incident_in.description,
        "category": incident_in.category.value,
        "severity": incident_in.severity.value,
        "location": incident_in.location,
        "latitude": incident_in.latitude,
        "longitude": incident_in.longitude,
        "image_url": incident_in.image_url,
        "status": IncidentStatus.REPORTED.value,
        "reporter_uid": current_user.uid,
        "reported_by": current_user.uid,
        "reporter_email": current_user.email,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    try:
        # Write to Cloud Firestore and verify
        db.collection("incidents").document(incident_id).set(incident_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firestore incident write failed: {exc}",
        ) from exc

    return IncidentResponse(
        id=incident_dict["id"],
        title=incident_dict["title"],
        description=incident_dict["description"],
        category=IncidentCategory(incident_dict["category"]),
        severity=IncidentSeverity(incident_dict["severity"]),
        location=incident_dict["location"],
        latitude=incident_dict["latitude"],
        longitude=incident_dict["longitude"],
        image_url=incident_dict["image_url"],
        status=IncidentStatus(incident_dict["status"]),
        reporter_uid=incident_dict["reporter_uid"],
        reported_by=incident_dict["reported_by"],
        reporter_email=incident_dict["reporter_email"],
        created_at=incident_dict["created_at"],
        updated_at=incident_dict["updated_at"],
    )


def list_incidents(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    current_user: Optional[UserPrincipal] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[int, List[IncidentResponse]]:
    """
    Retrieve community incident stream from Cloud Firestore with pagination and role-based permissions.
    COMMUNITY_USER: Strictly restricted to own submissions.
    ANALYST / ADMIN: Authorized to inspect all community submissions.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access incident records.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Cloud Firestore client is unavailable.")

    query = db.collection("incidents")
    if current_user.role == UserRole.COMMUNITY_USER:
        try:
            from google.cloud.firestore_v1 import FieldFilter
            query = query.where(filter=FieldFilter("reporter_uid", "==", current_user.uid))
        except Exception:
            query = query.where("reporter_uid", "==", current_user.uid)

    try:
        docs = list(query.stream())
        all_items: List[Dict[str, Any]] = [d.to_dict() for d in docs if d.to_dict()]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firestore incident query failed: {exc}",
        ) from exc

    filtered: List[Dict[str, Any]] = []
    for item in all_items:
        item_reporter = item.get("reporter_uid") or item.get("reported_by")
        if current_user.role == UserRole.COMMUNITY_USER and item_reporter != current_user.uid:
            continue
        if category and item.get("category") != category:
            continue
        if severity and item.get("severity") != severity:
            continue
        if status_filter and item.get("status") != status_filter:
            continue
        if search:
            term = search.lower()
            if not (term in item.get("title", "").lower() or term in item.get("location", "").lower() or term in item.get("id", "").lower()):
                continue
        filtered.append(item)

    # Sort descending by creation date
    sorted_items = sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(sorted_items)

    start = (page - 1) * page_size
    end = start + page_size
    paged_items = sorted_items[start:end]

    responses = [
        IncidentResponse(
            id=item["id"],
            title=item["title"],
            description=item["description"],
            category=IncidentCategory(item["category"]),
            severity=IncidentSeverity(item["severity"]),
            location=item["location"],
            latitude=item.get("latitude"),
            longitude=item.get("longitude"),
            image_url=item.get("image_url"),
            status=IncidentStatus(item.get("status", "reported")),
            reporter_uid=item.get("reporter_uid") or item.get("reported_by", ""),
            reported_by=item.get("reported_by") or item.get("reporter_uid", ""),
            reporter_email=item.get("reporter_email", ""),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
        )
        for item in paged_items
    ]

    return total, responses


def get_incident_by_id(incident_id: str, current_user: Optional[UserPrincipal] = None) -> IncidentResponse:
    """
    Retrieve an individual incident by server ID from Firestore with strict ownership validation.
    COMMUNITY_USER: Can only view their own reported incident.
    ANALYST / ADMIN: Can view any incident in the platform registry.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to inspect incident details.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Cloud Firestore client is unavailable.")

    try:
        doc = db.collection("incidents").document(incident_id).get()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firestore incident fetch failed: {exc}",
        ) from exc

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )

    incident_dict = doc.to_dict() or {}

    item_reporter = incident_dict.get("reporter_uid") or incident_dict.get("reported_by")
    if current_user.role == UserRole.COMMUNITY_USER and item_reporter != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Community users are restricted to accessing their own reported incidents.",
        )

    return IncidentResponse(
        id=incident_dict["id"],
        title=incident_dict["title"],
        description=incident_dict["description"],
        category=IncidentCategory(incident_dict["category"]),
        severity=IncidentSeverity(incident_dict["severity"]),
        location=incident_dict["location"],
        latitude=incident_dict.get("latitude"),
        longitude=incident_dict.get("longitude"),
        image_url=incident_dict.get("image_url"),
        status=IncidentStatus(incident_dict.get("status", "reported")),
        reporter_uid=item_reporter or "",
        reported_by=item_reporter or "",
        reporter_email=incident_dict.get("reporter_email", ""),
        created_at=incident_dict.get("created_at", ""),
        updated_at=incident_dict.get("updated_at", ""),
    )


def get_incident_stats(current_user: Optional[UserPrincipal] = None) -> IncidentStatsResponse:
    """
    Calculate real aggregate incident metrics from Cloud Firestore.
    If database contains zero incidents, returns zeros without fabrication.
    """
    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Cloud Firestore client is unavailable.")

    try:
        docs = list(db.collection("incidents").stream())
        all_items = [d.to_dict() for d in docs if d.to_dict()]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firestore incident stats query failed: {exc}",
        ) from exc

    total = len(all_items)
    if total == 0:
        return IncidentStatsResponse(
            total_incidents=0,
            active_incidents=0,
            resolved_incidents=0,
            high_severity_count=0,
            medium_severity_count=0,
            low_severity_count=0,
            category_counts={
                "waterlogging": 0,
                "road_damage": 0,
                "electrical_hazard": 0,
                "waste_management": 0,
                "extreme_heat": 0,
            },
            mean_risk_score=0.0,
        )

    active_count = sum(1 for i in all_items if i.get("status") in ["reported", "investigating", "mitigating"])
    resolved_count = sum(1 for i in all_items if i.get("status") == "resolved")
    high_count = sum(1 for i in all_items if i.get("severity") == "HIGH")
    medium_count = sum(1 for i in all_items if i.get("severity") == "MEDIUM")
    low_count = sum(1 for i in all_items if i.get("severity") == "LOW")

    category_counts = {
        "waterlogging": sum(1 for i in all_items if i.get("category") == "waterlogging"),
        "road_damage": sum(1 for i in all_items if i.get("category") == "road_damage"),
        "electrical_hazard": sum(1 for i in all_items if i.get("category") == "electrical_hazard"),
        "waste_management": sum(1 for i in all_items if i.get("category") == "waste_management"),
        "extreme_heat": sum(1 for i in all_items if i.get("category") == "extreme_heat"),
    }

    severity_weights = {"LOW": 20.0, "MEDIUM": 50.0, "HIGH": 80.0}
    scores = [severity_weights.get(i.get("severity", "MEDIUM"), 50.0) for i in all_items]
    mean_risk = round(sum(scores) / len(scores), 1) if scores else 0.0

    return IncidentStatsResponse(
        total_incidents=total,
        active_incidents=active_count,
        resolved_incidents=resolved_count,
        high_severity_count=high_count,
        medium_severity_count=medium_count,
        low_severity_count=low_count,
        category_counts=category_counts,
        mean_risk_score=mean_risk,
    )


def sync_user_profile(sync_data: ProfileSyncRequest, current_user: UserPrincipal) -> UserProfile:
    """
    Ensure user document exists in Cloud Firestore 'users/{uid}'.
    Strictly prevents self-escalation: self-registered users are guaranteed COMMUNITY_USER.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    uid = current_user.uid

    db = get_firestore_client()
    if db is None:
        raise RuntimeError("Cloud Firestore client is unavailable.")

    doc_ref = db.collection("users").document(uid)
    try:
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict() or {}
            existing_role = UserRole(data.get("role", UserRole.COMMUNITY_USER.value))
            display_name = sync_data.display_name or data.get("display_name")
            doc_ref.update({
                "display_name": display_name,
                "updated_at": now_iso,
            })
        else:
            existing_role = UserRole.COMMUNITY_USER
            display_name = sync_data.display_name
            doc_ref.set({
                "uid": uid,
                "email": current_user.email,
                "display_name": display_name,
                "role": UserRole.COMMUNITY_USER.value,
                "created_at": now_iso,
                "updated_at": now_iso,
            })
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firestore user profile sync failed: {exc}",
        ) from exc

    return UserProfile(
        uid=uid,
        email=current_user.email,
        display_name=display_name,
        role=existing_role,
        created_at=now_iso,
        updated_at=now_iso,
    )
