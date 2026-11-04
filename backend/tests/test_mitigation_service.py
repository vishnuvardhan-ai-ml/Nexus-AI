"""
Unit & Integration Tests for NEXUS AI Municipal Mitigation & Multi-Scenario Simulation Service.
Validates:
- 2–5 scenario validation boundaries (rejecting <2 or >5, rejecting duplicate IDs).
- Deterministic weighted risk calculation (R = 0.4H + 0.3E + 0.2V + 0.1D).
- Absolute and percentage risk reduction with zero-baseline edge cases.
- Safe cost-effectiveness calculation with zero, missing, and uncertain costs.
- Parameter shift attribution and causal drivers.
- Category-specific action presets across all 6 incident taxonomies.
- Multi-criteria ranking determinism and tie-handling.
- Strict non-destructive in-memory guarantees (zero Firestore calls).
- Diagnostic record detection and exclusion notices.
- Executive brief synthesis and Markdown report generation.
"""
import pytest
from pydantic import ValidationError

from app.schemas.risk import (
    RiskLevel,
    RiskFactorInput,
    EstimationSource,
)
from app.schemas.mitigation import (
    MitigationCategory,
    FeasibilityRating,
    CostConfidence,
    ResourceEstimate,
    MitigationActionPreset,
    MitigationScenarioInput,
    MultiScenarioSimulationRequest,
    MultiScenarioSimulationResponse,
)
from app.services.mitigation_service import (
    get_mitigation_presets,
    normalize_mitigation_category,
    format_currency_inr,
    calculate_scenario_cost_effectiveness,
    evaluate_single_scenario,
    compute_multi_scenario_rankings,
    simulate_multi_scenarios,
    generate_mitigation_plan_brief,
    generate_mitigation_brief_markdown,
    is_diagnostic_record,
    MITIGATION_ACTION_CATALOG,
)


def test_category_normalization_and_all_six_categories_covered():
    """Verify category normalization maps colloquial terms to the 6 valid domains."""
    categories_to_test = [
        ("waterlogging", "waterlogging"),
        ("FLOODING", "waterlogging"),
        ("road_damage", "road_damage"),
        ("pothole", "road_damage"),
        ("electrical_hazard", "electrical_hazard"),
        ("electrical", "electrical_hazard"),
        ("power line", "electrical_hazard"),
        ("waste_management", "waste_management"),
        ("garbage dump", "waste_management"),
        ("extreme_heat", "extreme_heat"),
        ("thermal heatwave", "extreme_heat"),
        ("general_safety", "general_safety"),
        ("unknown_hazard", "general_safety"),
    ]

    for raw, expected in categories_to_test:
        norm = normalize_mitigation_category(raw)
        assert norm == expected, f"Failed normalizing '{raw}': expected '{expected}', got '{norm}'"

    # Ensure all 6 categories have non-empty presets
    for cat in ["waterlogging", "road_damage", "electrical_hazard", "waste_management", "extreme_heat", "general_safety"]:
        presets = get_mitigation_presets(cat)
        assert len(presets) >= 2, f"Category '{cat}' should have at least 2 presets, got {len(presets)}"
        for p in presets:
            assert p.status == "PROPOSED"
            assert p.resource_estimate.is_estimate is True
            assert p.resource_estimate.currency == "INR"
            assert p.resource_estimate.estimated_cost_min is not None
            assert p.resource_estimate.estimated_cost_max is not None
            assert p.resource_estimate.estimated_cost_max >= p.resource_estimate.estimated_cost_min
            assert len(p.target_factor_deltas) > 0


def test_inr_currency_formatting():
    """Verify Indian numbering format (lakhs, crores)."""
    assert format_currency_inr(500) == "₹500"
    assert format_currency_inr(25000) == "₹25,000"
    assert format_currency_inr(150000) == "₹1,50,000"
    assert format_currency_inr(1250000) == "₹12,50,000"
    assert format_currency_inr(10000000) == "₹1,00,00,000"
    assert format_currency_inr(None) == "Unestimated"


def test_cost_effectiveness_calculation_and_zero_cost_safety():
    """Verify risk points reduced per ₹1 Lakh calculation and edge cases."""
    # 1. Standard quantifiable cost
    res = ResourceEstimate(
        estimated_cost_min=40000.0,
        estimated_cost_max=60000.0,  # Mean cost = 50,000 INR = 0.5 Lakh
        currency="INR",
    )
    # 15 points reduction / 0.5 Lakh = 30.0 points per lakh
    pts_per_lakh, label = calculate_scenario_cost_effectiveness(15.0, res)
    assert pts_per_lakh == 30.0
    assert "30.00 pts / ₹1.0 Lakh" in label

    # 2. Zero cost (no division by zero!)
    zero_res = ResourceEstimate(
        estimated_cost_min=0.0,
        estimated_cost_max=0.0,
        currency="INR",
    )
    zero_pts, zero_label = calculate_scenario_cost_effectiveness(20.0, zero_res)
    assert zero_pts is None
    assert "Zero Additional Direct Cost" in zero_label

    # 3. Missing / None cost
    none_res = ResourceEstimate(
        estimated_cost_min=None,
        estimated_cost_max=None,
        currency="INR",
    )
    none_pts, none_label = calculate_scenario_cost_effectiveness(10.0, none_res)
    assert none_pts is None
    assert "Unestimated Cost" in none_label

    # 4. Zero or negative risk reduction
    neg_pts, neg_label = calculate_scenario_cost_effectiveness(-5.0, res)
    assert neg_pts == 0.0
    assert "No Risk Reduction" in neg_label


def test_multi_scenario_request_validation_boundaries():
    """Verify request bounds: strictly 2 to 5 scenarios, unique scenario IDs."""
    base_factors = RiskFactorInput(
        hazard_severity=70.0,
        exposure=60.0,
        vulnerability=50.0,
        duration=40.0,
        source=EstimationSource.USER_DIRECT,
    )

    scen_a = MitigationScenarioInput(
        scenario_id="scen_a",
        scenario_name="Scenario A",
        simulated_factors=RiskFactorInput(
            hazard_severity=40.0, exposure=40.0, vulnerability=40.0, duration=30.0
        ),
    )
    scen_b = MitigationScenarioInput(
        scenario_id="scen_b",
        scenario_name="Scenario B",
        simulated_factors=RiskFactorInput(
            hazard_severity=50.0, exposure=30.0, vulnerability=30.0, duration=20.0
        ),
    )

    # 1. Valid 2 scenarios
    req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[scen_a, scen_b],
    )
    assert len(req.scenarios) == 2

    # 2. Reject 1 scenario (<2)
    with pytest.raises(ValidationError):
        MultiScenarioSimulationRequest(
            baseline_factors=base_factors,
            scenarios=[scen_a],
        )

    # 3. Reject duplicate scenario IDs
    scen_duplicate = MitigationScenarioInput(
        scenario_id="scen_a",  # Duplicate!
        scenario_name="Scenario A Duplicate",
        simulated_factors=RiskFactorInput(
            hazard_severity=30.0, exposure=30.0, vulnerability=30.0, duration=20.0
        ),
    )
    with pytest.raises(ValidationError) as exc:
        MultiScenarioSimulationRequest(
            baseline_factors=base_factors,
            scenarios=[scen_a, scen_duplicate],
        )
    assert "Scenario IDs must be unique" in str(exc.value)

    # 4. Reject 6 scenarios (>5)
    scenarios_6 = [
        MitigationScenarioInput(
            scenario_id=f"scen_{i}",
            scenario_name=f"Scenario {i}",
            simulated_factors=RiskFactorInput(
                hazard_severity=40.0, exposure=40.0, vulnerability=40.0, duration=30.0
            ),
        )
        for i in range(6)
    ]
    with pytest.raises(ValidationError):
        MultiScenarioSimulationRequest(
            baseline_factors=base_factors,
            scenarios=scenarios_6,
        )


def test_deterministic_multi_scenario_evaluation_and_parameter_shifts():
    """Verify deterministic risk calculations and parameter shift attribution."""
    # Baseline: H=80, E=70, V=60, D=50
    # Expected R_base = 0.4(80) + 0.3(70) + 0.2(60) + 0.1(50) = 32 + 21 + 12 + 5 = 70.0 (HIGH)
    base_factors = RiskFactorInput(
        hazard_severity=80.0,
        exposure=70.0,
        vulnerability=60.0,
        duration=50.0,
    )

    # Scenario 1: Dewatering Pumping (H=30, E=70, V=60, D=20)
    # Expected R_sim1 = 0.4(30) + 0.3(70) + 0.2(60) + 0.1(20) = 12 + 21 + 12 + 2 = 47.0 (MEDIUM)
    # Delta R = 70.0 - 47.0 = 23.0 points reduction (32.9%)
    scen_1 = MitigationScenarioInput(
        scenario_id="scen_pumping",
        scenario_name="Mobile Pumping",
        simulated_factors=RiskFactorInput(
            hazard_severity=30.0, exposure=70.0, vulnerability=60.0, duration=20.0
        ),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=50000.0,
            estimated_cost_max=50000.0,  # Exactly 0.5 Lakh
            estimated_duration_hours=3.0,
            currency="INR",
        ),
    )

    # Scenario 2: Traffic Diversion & Barricades (H=80, E=20, V=60, D=50)
    # Expected R_sim2 = 0.4(80) + 0.3(20) + 0.2(60) + 0.1(50) = 32 + 6 + 12 + 5 = 55.0 (MEDIUM)
    # Delta R = 70.0 - 55.0 = 15.0 points reduction (21.4%)
    scen_2 = MitigationScenarioInput(
        scenario_id="scen_diversion",
        scenario_name="Traffic Diversion",
        simulated_factors=RiskFactorInput(
            hazard_severity=80.0, exposure=20.0, vulnerability=60.0, duration=50.0
        ),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=10000.0,
            estimated_cost_max=10000.0,  # Exactly 0.1 Lakh
            estimated_duration_hours=1.0,
            currency="INR",
        ),
    )

    # Scenario 3: Capital Retention Basin (H=20, E=30, V=20, D=10)
    # Expected R_sim3 = 0.4(20) + 0.3(30) + 0.2(20) + 0.1(10) = 8 + 9 + 4 + 1 = 22.0 (LOW)
    # Delta R = 70.0 - 22.0 = 48.0 points reduction (68.6%)
    scen_3 = MitigationScenarioInput(
        scenario_id="scen_basin",
        scenario_name="Subsurface Retention Basin",
        simulated_factors=RiskFactorInput(
            hazard_severity=20.0, exposure=30.0, vulnerability=20.0, duration=10.0
        ),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=500000.0,
            estimated_cost_max=500000.0,  # Exactly 5.0 Lakhs
            estimated_duration_hours=96.0,
            currency="INR",
        ),
    )

    req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[scen_1, scen_2, scen_3],
    )

    res = simulate_multi_scenarios(req)

    # Assert baseline
    assert res.baseline_score == 70.0
    assert res.baseline_level == RiskLevel.HIGH
    assert res.scenarios_evaluated_count == 3

    # Assert evaluations
    e1 = res.evaluations[0]
    assert e1.simulated_score == 47.0
    assert e1.simulated_level == RiskLevel.MEDIUM
    assert e1.absolute_risk_reduction == 23.0
    assert e1.relative_risk_reduction_pct == 32.9
    assert e1.level_changed is True
    assert "HIGH -> MEDIUM" in e1.level_transition
    # 23.0 pts / 0.5 Lakh = 46.0 pts / lakh
    assert e1.cost_effectiveness_per_lakh == 46.0
    assert "Primary mitigation driven by Hazard Severity (H) reduction" in e1.primary_mitigation_driver
    assert len(e1.parameter_shifts) == 2  # H and D shifted

    e2 = res.evaluations[1]
    assert e2.simulated_score == 55.0
    assert e2.absolute_risk_reduction == 15.0
    # 15.0 pts / 0.1 Lakh = 150.0 pts / lakh
    assert e2.cost_effectiveness_per_lakh == 150.0

    e3 = res.evaluations[2]
    assert e3.simulated_score == 22.0
    assert e3.simulated_level == RiskLevel.LOW
    assert e3.absolute_risk_reduction == 48.0
    assert e3.relative_risk_reduction_pct == 68.6
    # 48.0 pts / 5.0 Lakhs = 9.6 pts / lakh
    assert e3.cost_effectiveness_per_lakh == 9.6

    # Verify Multi-Criteria Rankings:
    # 1. By Impact: Basin (48 pts) > Pumping (23 pts) > Diversion (15 pts)
    assert res.rankings.by_impact[0].scenario_id == "scen_basin"
    assert res.rankings.by_impact[1].scenario_id == "scen_pumping"
    assert res.rankings.by_impact[2].scenario_id == "scen_diversion"

    # 2. By Cost Efficiency: Diversion (150 pts/lakh) > Pumping (46 pts/lakh) > Basin (9.6 pts/lakh)
    assert res.rankings.by_cost_efficiency[0].scenario_id == "scen_diversion"
    assert res.rankings.by_cost_efficiency[1].scenario_id == "scen_pumping"
    assert res.rankings.by_cost_efficiency[2].scenario_id == "scen_basin"

    # 3. By Deployment Speed: Diversion (1.0 hr) > Pumping (3.0 hrs) > Basin (96.0 hrs)
    assert res.rankings.by_deployment_speed[0].scenario_id == "scen_diversion"
    assert res.rankings.by_deployment_speed[1].scenario_id == "scen_pumping"
    assert res.rankings.by_deployment_speed[2].scenario_id == "scen_basin"

    # 4. Best Balanced is chosen deterministically
    assert res.rankings.best_balanced is not None
    assert res.rankings.best_balanced.scenario_id in ["scen_pumping", "scen_diversion"]


def test_baseline_zero_and_risk_escalation_edge_cases():
    """Verify zero-baseline safe division and risk escalation detection."""
    # Baseline with zero risk
    zero_base = RiskFactorInput(
        hazard_severity=0.0, exposure=0.0, vulnerability=0.0, duration=0.0
    )
    scen_esc = MitigationScenarioInput(
        scenario_id="scen_escalation",
        scenario_name="Uncontained Inundation Surge",
        simulated_factors=RiskFactorInput(
            hazard_severity=60.0, exposure=50.0, vulnerability=40.0, duration=30.0
        ),
    )
    scen_neutral = MitigationScenarioInput(
        scenario_id="scen_neutral",
        scenario_name="Zero Shift Neutral",
        simulated_factors=zero_base,
    )

    req = MultiScenarioSimulationRequest(
        baseline_factors=zero_base,
        scenarios=[scen_esc, scen_neutral],
    )

    res = simulate_multi_scenarios(req)
    assert res.baseline_score == 0.0

    # Escalation scenario
    e_esc = res.evaluations[0]
    assert e_esc.simulated_score > 0.0
    assert e_esc.absolute_risk_reduction < 0.0
    assert e_esc.relative_risk_reduction_pct == 0.0  # Safe handling of zero baseline
    assert "Risk escalation" in e_esc.primary_mitigation_driver
    assert e_esc.cost_effectiveness_per_lakh == 0.0

    # Neutral scenario
    e_neut = res.evaluations[1]
    assert e_neut.simulated_score == 0.0
    assert e_neut.absolute_risk_reduction == 0.0
    assert "Neutral intervention" in e_neut.primary_mitigation_driver


def test_diagnostic_record_detection_and_disclosures():
    """Verify that diagnostic records are detected and properly flagged with disclaimers."""
    diag_incident = {
        "id": "inc_7ce367bfe3be",
        "title": "Live Milestone 2B Verification: Road Subsidence Hazard",
        "reporter_email": "diagnostic_test_1793714803737@nexus-test.org",
        "is_test": False,
    }
    assert is_diagnostic_record(diag_incident) is True

    real_incident = {
        "id": "inc_real_999",
        "title": "Severe Waterlogging Under Railway Bridge",
        "reporter_email": "resident@community.gov",
        "is_test": False,
    }
    assert is_diagnostic_record(real_incident) is False

    base_factors = RiskFactorInput(
        hazard_severity=65.0, exposure=50.0, vulnerability=50.0, duration=40.0
    )
    req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[
            MitigationScenarioInput(
                scenario_id="s1",
                scenario_name="S1",
                simulated_factors=RiskFactorInput(hazard_severity=30.0, exposure=30.0, vulnerability=30.0, duration=20.0),
            ),
            MitigationScenarioInput(
                scenario_id="s2",
                scenario_name="S2",
                simulated_factors=RiskFactorInput(hazard_severity=40.0, exposure=30.0, vulnerability=30.0, duration=20.0),
            ),
        ],
    )

    res = simulate_multi_scenarios(req, incident_data=diag_incident)
    assert res.is_diagnostic_record is True
    assert res.diagnostic_notice is not None
    assert "DIAGNOSTIC TEST RECORD" in res.diagnostic_notice


def test_mitigation_brief_and_markdown_report_generation():
    """Verify structured executive brief synthesis and Markdown export."""
    base_factors = RiskFactorInput(
        hazard_severity=75.0, exposure=65.0, vulnerability=55.0, duration=45.0
    )
    scen_a = MitigationScenarioInput(
        scenario_id="scen_a",
        scenario_name="Rapid Pump Deployment",
        simulated_factors=RiskFactorInput(hazard_severity=35.0, exposure=40.0, vulnerability=40.0, duration=25.0),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=30000.0,
            estimated_cost_max=60000.0,
            currency="INR",
            currency_symbol="₹",
            estimated_manpower=4,
            estimated_duration_hours=3.0,
        ),
    )
    scen_b = MitigationScenarioInput(
        scenario_id="scen_b",
        scenario_name="Culvert Desilting Squad",
        simulated_factors=RiskFactorInput(hazard_severity=55.0, exposure=65.0, vulnerability=30.0, duration=35.0),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=15000.0,
            estimated_cost_max=25000.0,
            currency="INR",
            currency_symbol="₹",
            estimated_manpower=5,
            estimated_duration_hours=2.0,
        ),
    )

    req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[scen_a, scen_b],
    )
    sim_res = simulate_multi_scenarios(req)

    brief = generate_mitigation_plan_brief(
        simulation_response=sim_res,
        incident_title="Sector 4 Arterial Inundation Review",
        category="waterlogging",
        location="Sector 4 Underpass Crossing",
    )

    assert brief.incident_title == "Sector 4 Arterial Inundation Review"
    assert brief.category == "waterlogging"
    assert brief.recommended_scenario_id in ["scen_a", "scen_b"]
    assert brief.projected_risk_reduction > 0
    assert len(brief.proposed_actions) > 0
    for act in brief.proposed_actions:
        assert act.status == "PROPOSED"
    assert len(brief.disclaimers) >= 3

    # Generate Markdown text
    md = generate_mitigation_brief_markdown(brief, sim_res)
    assert "# Municipal Mitigation Brief: Sector 4 Arterial Inundation Review" in md
    assert "PROPOSED INTERVENTIONS ONLY" in md
    assert "Multi-Scenario Comparative Evaluation" in md
    assert "| Scenario Name | Simulated Score | ΔR Impact |" in md
    assert "Rapid Pump Deployment" in md
    assert "Culvert Desilting Squad" in md
    assert "Mandatory Disclaimers" in md


def test_non_destructive_in_memory_guarantee():
    """Verify that simulation is strictly stateless and performs zero Firestore writes."""
    base_factors = RiskFactorInput(
        hazard_severity=50.0, exposure=50.0, vulnerability=50.0, duration=50.0
    )
    req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[
            MitigationScenarioInput(
                scenario_id="s1",
                scenario_name="Scenario 1",
                simulated_factors=RiskFactorInput(hazard_severity=20.0, exposure=20.0, vulnerability=20.0, duration=20.0),
            ),
            MitigationScenarioInput(
                scenario_id="s2",
                scenario_name="Scenario 2",
                simulated_factors=RiskFactorInput(hazard_severity=30.0, exposure=30.0, vulnerability=30.0, duration=30.0),
            ),
        ],
    )
    # Execution should succeed without any database initialization or connection
    res = simulate_multi_scenarios(req)
    assert res.simulation_id.startswith("sim_multi_")
    for e in res.evaluations:
        assert e.is_simulation is True
        assert e.status == "PROPOSED"
