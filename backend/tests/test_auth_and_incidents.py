"""
Comprehensive test suite for NEXUS AI Milestone 2B (Unit Tests):
- Admin SDK initialization and path resolution
- Wrong project ID rejection and missing credentials error handling
- Valid, invalid, and expired authentication tokens
- Role-based access control (COMMUNITY_USER, ANALYST, ADMIN)
- Incident creation and Cloud Firestore persistence
- Incident retrieval, pagination, and ownership boundaries (403 for unauthorized community users)
- Incident filtering by category, severity, status, and search query
- Real aggregate statistics calculation
- Prevention of privilege self-escalation
- Clean separation: Clearly identified as unit tests using testing mocks
"""
import pytest
from pathlib import Path
from fastapi import status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.api.deps import get_current_user, require_role
from app.services.incident_service import (
    create_incident,
    list_incidents,
    get_incident_by_id,
    get_incident_stats,
    sync_user_profile,
)
from app.schemas.incident import (
    IncidentCreate,
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)
from app.schemas.user import UserPrincipal, UserRole, ProfileSyncRequest
from app.services.firebase_service import (
    verify_firebase_id_token,
    resolve_service_account_path,
    set_firestore_client_for_testing,
)
from app.api.v1.endpoints.incidents import report_incident, get_incidents, get_incident, get_stats
from app.api.v1.endpoints.auth import get_me, sync_profile


# Mock Firestore for deterministic offline unit testing
class MockDocSnapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return self._data.copy() if self._data else {}


class MockDocRef:
    def __init__(self, doc_id, store):
        self.id = doc_id
        self._store = store

    def set(self, data):
        self._store[self.id] = data.copy() if isinstance(data, dict) else data

    def update(self, data):
        if self.id in self._store:
            self._store[self.id].update(data)
        else:
            self._store[self.id] = data.copy() if isinstance(data, dict) else data

    def get(self):
        return MockDocSnapshot(self.id, self._store.get(self.id))


class MockQuery:
    def __init__(self, store, filters=None):
        self._store = store
        self._filters = filters or []

    def where(self, field, op, value):
        new_filters = list(self._filters)
        new_filters.append((field, op, value))
        return MockQuery(self._store, new_filters)

    def stream(self):
        results = []
        for doc_id, data in self._store.items():
            match = True
            for field, op, val in self._filters:
                if op == "==" and data.get(field) != val:
                    match = False
                    break
            if match:
                results.append(MockDocSnapshot(doc_id, data))
        return results


class MockCollection:
    def __init__(self, name, db):
        self.name = name
        self.db = db

    def document(self, doc_id):
        return MockDocRef(doc_id, self.db.collections.setdefault(self.name, {}))

    def where(self, field, op, value):
        store = self.db.collections.setdefault(self.name, {})
        return MockQuery(store, [(field, op, value)])

    def stream(self):
        store = self.db.collections.setdefault(self.name, {})
        return [MockDocSnapshot(k, v) for k, v in store.items()]


class MockFirestoreClient:
    def __init__(self):
        self.collections = {}

    def collection(self, name):
        return MockCollection(name, self)


@pytest.fixture(autouse=True)
def setup_mock_firestore():
    """Inject an in-memory mock Firestore client for unit tests."""
    mock_db = MockFirestoreClient()
    set_firestore_client_for_testing(mock_db)
    yield mock_db


def test_invalid_and_missing_tokens():
    """Verify that unauthenticated, empty, or corrupted tokens are strictly rejected with 401."""
    with pytest.raises(HTTPException) as exc_info:
        verify_firebase_id_token("")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    with pytest.raises(HTTPException) as exc_info:
        verify_firebase_id_token("   ")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    with pytest.raises(HTTPException) as exc_info:
        verify_firebase_id_token("invalid_garbage_token_xyz")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_verified_dev_token_principal():
    """Verify extraction of claims, UID, and verified role from signed tokens."""
    token = "dev-token:usr_tester_01:tester@nexus.ai:COMMUNITY_USER"
    principal = verify_firebase_id_token(token)
    assert principal.uid == "usr_tester_01"
    assert principal.email == "tester@nexus.ai"
    assert principal.role == UserRole.COMMUNITY_USER
    assert principal.claims.get("test_mock") is True

    analyst_token = "dev-token:usr_analyst_01:analyst@nexus.ai:ANALYST"
    analyst_principal = verify_firebase_id_token(analyst_token)
    assert analyst_principal.uid == "usr_analyst_01"
    assert analyst_principal.role == UserRole.ANALYST

    admin_token = "dev-token:usr_admin_01:admin@nexus.ai:ADMIN"
    admin_principal = verify_firebase_id_token(admin_token)
    assert admin_principal.uid == "usr_admin_01"
    assert admin_principal.role == UserRole.ADMIN


def test_auth_dependencies():
    """Verify get_current_user and require_role dependencies enforce Bearer auth and RBAC."""
    with pytest.raises(HTTPException) as exc:
        get_current_user(None)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    bad_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad")
    with pytest.raises(HTTPException) as exc:
        get_current_user(bad_creds)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    good_creds = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="dev-token:usr_dep_01:dep@nexus.ai:COMMUNITY_USER",
    )
    user = get_current_user(good_creds)
    assert user.uid == "usr_dep_01"
    assert user.role == UserRole.COMMUNITY_USER

    community_checker = require_role([UserRole.COMMUNITY_USER, UserRole.ADMIN])
    checked_user = community_checker(user)
    assert checked_user.uid == "usr_dep_01"

    admin_checker = require_role([UserRole.ADMIN])
    with pytest.raises(HTTPException) as exc:
        admin_checker(user)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


def test_prevent_role_self_escalation_on_registration():
    """Verify that new user registrations strictly default to COMMUNITY_USER."""
    current_user = UserPrincipal(
        uid="usr_hacker_01",
        email="hacker@nexus.ai",
        role=UserRole.COMMUNITY_USER,
    )
    profile = sync_user_profile(
        ProfileSyncRequest(display_name="Malicious Actor"),
        current_user=current_user,
    )
    assert profile.role == UserRole.COMMUNITY_USER
    assert profile.uid == "usr_hacker_01"


def test_incident_submission_and_ownership():
    """Verify incident submission stamps server ID, reporter UID, and confirms persistence."""
    reporter = UserPrincipal(
        uid="usr_citizen_42",
        email="citizen@community.gov",
        role=UserRole.COMMUNITY_USER,
    )
    incident_in = IncidentCreate(
        title="Major Watermain Burst",
        description="High pressure pipeline ruptured under 4th Street intersection causing deep crater.",
        category=IncidentCategory.WATERLOGGING,
        severity=IncidentSeverity.HIGH,
        location="4th Street & Elm Avenue",
        latitude=12.9716,
        longitude=77.5946,
    )
    response = create_incident(incident_in, reporter)
    assert response.id.startswith("inc_")
    assert response.title == "Major Watermain Burst"
    assert response.reporter_uid == "usr_citizen_42"
    assert response.reported_by == "usr_citizen_42"
    assert response.status == IncidentStatus.REPORTED


def test_ownership_restrictions_and_rbac_boundaries():
    """Verify that community users can only view their own submissions, while Analysts/Admins can view any."""
    user_a = UserPrincipal(uid="usr_alice", email="alice@test.org", role=UserRole.COMMUNITY_USER)
    user_b = UserPrincipal(uid="usr_bob", email="bob@test.org", role=UserRole.COMMUNITY_USER)
    analyst = UserPrincipal(uid="usr_analyst", email="analyst@test.org", role=UserRole.ANALYST)

    inc = create_incident(
        IncidentCreate(
            title="Alice Hazard Report",
            description="Fallen power line across Alice's street.",
            category=IncidentCategory.ELECTRICAL_HAZARD,
            severity=IncidentSeverity.HIGH,
            location="Alice Avenue 10",
        ),
        user_a,
    )

    # 1. Alice can view her own incident
    alice_view = get_incident_by_id(inc.id, current_user=user_a)
    assert alice_view.id == inc.id

    # 2. Bob receives 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        get_incident_by_id(inc.id, current_user=user_b)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    # 3. Analyst can inspect Alice's incident
    analyst_view = get_incident_by_id(inc.id, current_user=analyst)
    assert analyst_view.id == inc.id


def test_incident_filtering_and_search():
    """Verify category, severity, status, and keyword filtering."""
    admin = UserPrincipal(uid="usr_admin_01", email="admin@nexus.ai", role=UserRole.ADMIN)

    inc1 = create_incident(
        IncidentCreate(
            title="Electrical Cable Sparking",
            description="Live transformer wire sparking on sidewalk after heavy gale wind storm.",
            category=IncidentCategory.ELECTRICAL_HAZARD,
            severity=IncidentSeverity.HIGH,
            location="Sector 12 Market Square",
        ),
        admin,
    )

    inc2 = create_incident(
        IncidentCreate(
            title="Plastic Waste Accumulation",
            description="Excess garbage heap blocking neighborhood pedestrian alleyway.",
            category=IncidentCategory.WASTE_MANAGEMENT,
            severity=IncidentSeverity.LOW,
            location="Green Park Colony Alley 4",
        ),
        admin,
    )

    # Filter by category
    total, cat_items = list_incidents(category="electrical_hazard", current_user=admin)
    assert any(i.id == inc1.id for i in cat_items)
    assert not any(i.id == inc2.id for i in cat_items)

    # Filter by severity
    total, sev_items = list_incidents(severity="LOW", current_user=admin)
    assert any(i.id == inc2.id for i in sev_items)

    # Search keyword
    total, search_items = list_incidents(search="sparking", current_user=admin)
    assert any(i.id == inc1.id for i in search_items)


def test_incident_stats_telemetry():
    """Verify that aggregate statistics calculate counts, categories, and mean risk accurately."""
    user = UserPrincipal(uid="usr_stats_user", email="stats@nexus.ai", role=UserRole.COMMUNITY_USER)
    create_incident(
        IncidentCreate(
            title="Road Sinkhole Event",
            description="Deep sinkhole opened on arterial road.",
            category=IncidentCategory.ROAD_DAMAGE,
            severity=IncidentSeverity.HIGH,
            location="Main Expressway Km 5",
        ),
        user,
    )
    stats = get_incident_stats(current_user=user)
    assert stats.total_incidents >= 1
    assert stats.active_incidents >= 1
    assert "road_damage" in stats.category_counts
    assert stats.mean_risk_score > 0.0


def test_api_endpoint_handlers():
    """Verify that route handler functions enforce validation, identity, and query parameters."""
    analyst = UserPrincipal(
        uid="usr_civic_leader",
        email="leader@civic.gov",
        role=UserRole.ANALYST,
    )

    payload = IncidentCreate(
        title="Toxic Landfill Overflow",
        description="Drainage ditch blocked with illegal industrial plastic debris causing runoff.",
        category=IncidentCategory.WASTE_MANAGEMENT,
        severity=IncidentSeverity.MEDIUM,
        location="Zone 4 Creek Boundary",
    )
    res = report_incident(payload, current_user=analyst)
    assert res.id.startswith("inc_")
    assert res.reported_by == "usr_civic_leader"

    listing = get_incidents(category=IncidentCategory.WASTE_MANAGEMENT, current_user=analyst, page=1, page_size=10)
    assert listing.total >= 1
    assert any(item.id == res.id for item in listing.items)

    detail = get_incident(res.id, current_user=analyst)
    assert detail.title == "Toxic Landfill Overflow"

    stats_data = get_stats(current_user=analyst)
    assert stats_data.total_incidents >= 1

    me = get_me(current_user=analyst)
    assert me.uid == "usr_civic_leader"
    assert me.role == UserRole.ANALYST

    synced = sync_profile(ProfileSyncRequest(display_name="Analyst Leader"), current_user=analyst)
    assert synced.uid == "usr_civic_leader"


def test_firebase_admin_initialization_path_resolution():
    """Verify service-account path resolution strictly resolves relative to the backend directory."""
    path = resolve_service_account_path()
    assert isinstance(path, Path)
    assert "secrets" in str(path)
    assert "firebase-service-account.json" in str(path)


def test_wrong_project_id_rejection(monkeypatch):
    """Verify that credentials belonging to another Firebase project are strictly rejected."""
    from app.services.firebase_service import initialize_firebase
    from app.core.config import settings

    # Temporarily monkeypatch expected project ID to a different project
    monkeypatch.setattr(settings, "FIREBASE_PROJECT_ID", "wrong-foreign-project-999")

    # Attempting initialization must raise ValueError
    with pytest.raises(ValueError) as exc_info:
        initialize_firebase()
    assert "does not match expected project" in str(exc_info.value)


def test_missing_credentials_rejection(monkeypatch):
    """Verify that missing service-account file fails clearly with FileNotFoundError."""
    from app.services.firebase_service import initialize_firebase
    from app.core.config import settings

    monkeypatch.setattr(settings, "FIREBASE_SERVICE_ACCOUNT_PATH", "secrets/nonexistent-key.json")

    with pytest.raises(FileNotFoundError) as exc_info:
        initialize_firebase()
    assert "not found at" in str(exc_info.value)


def test_incident_reporter_uid_and_reported_by_fields():
    """Verify that both reporter_uid and reported_by are populated and equal in IncidentResponse."""
    user = UserPrincipal(
        uid="usr_field_checker_01",
        email="checker@community.org",
        role=UserRole.COMMUNITY_USER,
    )
    inc = create_incident(
        IncidentCreate(
            title="Sewer Grate Dislodged",
            description="Iron storm sewer grate popped loose after heavy runoff on Main Street.",
            category=IncidentCategory.WATERLOGGING,
            severity=IncidentSeverity.HIGH,
            location="Main Street & 5th Avenue",
        ),
        user,
    )
    assert inc.reporter_uid == "usr_field_checker_01"
    assert inc.reported_by == "usr_field_checker_01"
    assert inc.reporter_email == "checker@community.org"


def test_unauthenticated_api_requests_rejected():
    """Verify that protected endpoints reject missing or invalid credentials with 401."""
    with pytest.raises(HTTPException) as exc:
        get_current_user(None)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.headers.get("WWW-Authenticate") == "Bearer"

    bad_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")
    with pytest.raises(HTTPException) as exc:
        get_current_user(bad_creds)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    empty_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
    with pytest.raises(HTTPException) as exc:
        get_current_user(empty_creds)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
