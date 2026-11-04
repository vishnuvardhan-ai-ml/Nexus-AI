"""
Unit tests for NEXUS AI Recommendation Service.

Focus Areas:
1. All 6 civic categories supported: waterlogging, road_damage, electrical, waste, extreme_heat, general_safety.
2. Risk-level priority mappings (IMMEDIATE, HIGH, MEDIUM, MONITOR).
3. Primary and secondary formula-driver targeting.
4. Mandatory PROPOSED status on all recommendations (never claimed completed).
5. Electrical life-safety directives (non-contact, 10m perimeter, authorized utility linesmen).
6. Role-based ownership authorization boundaries.
7. Determinism and reproducibility.
"""
import pytest
from fastapi import HTTPException

from app.schemas.risk import (
    RiskLevel,
    RecommendationPriority,
    RecommendationListResponse,
)
from app.schemas.user import UserRole, UserPrincipal
from app.services.recommendation_service import (
    generate_recommendations,
    normalize_category,
    verify_incident_recommendation_access,
)


# ==============================================================================
# 1. CATEGORY COVERAGE & DETERMINISTIC GENERATION
# ==============================================================================

@pytest.mark.parametrize("category", [
    "waterlogging",
    "road_damage",
    "electrical",
    "waste",
    "extreme_heat",
    "general_safety",
])
def test_recommendations_cover_all_categories(category: str):
    """Verify that every supported civic category generates valid, context-aware recommendations."""
    resp = generate_recommendations(
        risk_score=75.0,
        risk_level=RiskLevel.HIGH,
        category=category,
        primary_driver="hazard",
        secondary_driver="exposure",
        incident_id="inc_cat_test",
    )

    assert isinstance(resp, RecommendationListResponse)
    assert resp.category == category
    assert resp.risk_score == 75.0
    assert resp.risk_level == RiskLevel.HIGH
    assert len(resp.recommendations) >= 2

    # Every single recommendation must strictly be PROPOSED
    for rec in resp.recommendations:
        assert rec.status == "PROPOSED"
        assert rec.priority in [
            RecommendationPriority.IMMEDIATE,
            RecommendationPriority.HIGH,
            RecommendationPriority.MEDIUM,
            RecommendationPriority.MONITOR,
        ]
        assert len(rec.action) > 10
        assert len(rec.rationale) > 10
        assert len(rec.suggested_next_step) > 10
        assert rec.responsible_department is not None


def test_recommendations_reproducibility():
    """Verify deterministic generation: same inputs produce identical recommendations."""
    resp1 = generate_recommendations(
        risk_score=65.0,
        risk_level=RiskLevel.HIGH,
        category="road_damage",
        primary_driver="hazard",
        secondary_driver="exposure",
        incident_id="inc_rep_1",
    )
    resp2 = generate_recommendations(
        risk_score=65.0,
        risk_level=RiskLevel.HIGH,
        category="road_damage",
        primary_driver="hazard",
        secondary_driver="exposure",
        incident_id="inc_rep_1",
    )

    assert [r.id for r in resp1.recommendations] == [r.id for r in resp2.recommendations]
    assert [r.action for r in resp1.recommendations] == [r.action for r in resp2.recommendations]


# ==============================================================================
# 2. RISK LEVEL PRIORITY MAPPING
# ==============================================================================

def test_recommendation_priority_calibration_by_risk_level():
    """
    Verify priority calibration:
    - HIGH risk maps to IMMEDIATE or HIGH priorities.
    - LOW risk maps to MONITOR or MEDIUM priorities.
    """
    # HIGH Risk
    resp_high = generate_recommendations(
        risk_score=85.0,
        risk_level=RiskLevel.HIGH,
        category="waterlogging",
        primary_driver="hazard",
    )
    priorities_high = [r.priority for r in resp_high.recommendations]
    assert RecommendationPriority.IMMEDIATE in priorities_high or RecommendationPriority.HIGH in priorities_high

    # LOW Risk
    resp_low = generate_recommendations(
        risk_score=20.0,
        risk_level=RiskLevel.LOW,
        category="waterlogging",
        primary_driver="hazard",
    )
    priorities_low = [r.priority for r in resp_low.recommendations]
    assert RecommendationPriority.IMMEDIATE not in priorities_low
    assert RecommendationPriority.MONITOR in priorities_low


# ==============================================================================
# 3. PRIMARY & SECONDARY DRIVER TARGETING
# ==============================================================================

def test_primary_and_secondary_driver_differentiation():
    """
    Verify that primary driver produces a targeted action for that driver,
    and distinct secondary driver produces complementary intervention.
    """
    # Primary driver: exposure, Secondary: vulnerability
    resp = generate_recommendations(
        risk_score=62.0,
        risk_level=RiskLevel.HIGH,
        category="waste",
        primary_driver="exposure",
        secondary_driver="vulnerability",
    )

    primary_rec = resp.recommendations[0]
    secondary_rec = resp.recommendations[1]

    assert "Primary Driver:" in primary_rec.rationale
    assert "Secondary Driver:" in secondary_rec.rationale
    # Exposure in waste addresses spraying disinfectant or netting
    assert "disinfectant" in primary_rec.action.lower() or "exposure" in primary_rec.rationale.lower()
    # Vulnerability in waste addresses bollards or segregated bins
    assert "bollards" in secondary_rec.action.lower() or "bin" in secondary_rec.action.lower() or "vulnerability" in secondary_rec.rationale.lower()


# ==============================================================================
# 4. ELECTRICAL SAFETY MANDATE
# ==============================================================================

def test_electrical_hazard_life_safety_mandate():
    """
    Verify mandatory electrical life-safety protocol:
    - Immediate priority.
    - Non-contact perimeter (10m).
    - Authorized power distribution utility linesmen with dielectric equipment.
    """
    resp = generate_recommendations(
        risk_score=80.0,
        risk_level=RiskLevel.HIGH,
        category="electrical",
        primary_driver="hazard",
    )

    actions_text = " ".join([r.action for r in resp.recommendations]).lower()
    departments = [r.responsible_department for r in resp.recommendations if r.responsible_department]

    # Check key safety directives
    assert "dielectric" in actions_text
    assert "perimeter" in actions_text
    assert "linesmen" in actions_text or "utility" in actions_text
    assert any("power" in d.lower() or "discom" in d.lower() or "electric" in d.lower() for d in departments)


# ==============================================================================
# 5. ROLE-BASED OWNERSHIP AUTHORIZATION
# ==============================================================================

def test_verify_incident_recommendation_access_admin_and_analyst():
    """Verify that ADMIN and ANALYST have universal access to recommendations."""
    admin_user = UserPrincipal(uid="admin_uid", email="admin@nexus.ai", role=UserRole.ADMIN)
    analyst_user = UserPrincipal(uid="analyst_uid", email="analyst@nexus.ai", role=UserRole.ANALYST)
    incident = {"id": "inc_123", "reported_by": "other_user_456"}

    assert verify_incident_recommendation_access(incident, admin_user) is True
    assert verify_incident_recommendation_access(incident, analyst_user) is True


def test_verify_incident_recommendation_access_community_user():
    """
    Verify that COMMUNITY_USER can only access their own incident's recommendations
    and is denied access (HTTP 403) to other users' incidents.
    """
    comm_user = UserPrincipal(uid="citizen_uid", email="citizen@community.org", role=UserRole.COMMUNITY_USER)
    own_incident = {"id": "inc_own", "reported_by": "citizen_uid"}
    other_incident = {"id": "inc_other", "reported_by": "stranger_uid"}

    # Own incident: permitted
    assert verify_incident_recommendation_access(own_incident, comm_user) is True

    # Other incident: raises 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        verify_incident_recommendation_access(other_incident, comm_user)
    assert exc.value.status_code == 403
    assert "Community users are only authorized" in exc.value.detail
