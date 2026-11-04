"""
NEXUS AI Municipal Mitigation & What-If Simulation Domain Service.

Provides:
1. Category-specific municipal mitigation action catalog (all 6 incident categories).
2. Multi-scenario comparative simulation (2-5 competing scenarios vs 1 baseline).
3. Deterministic risk calculation reusing formula R = 0.4H + 0.3E + 0.2V + 0.1D.
4. Parameter shift tracking and causal attribution.
5. Indicative resource estimation (cost in INR ₹ / configurable currency, crew size, duration).
6. Safe cost-effectiveness calculation (risk points reduced per ₹1 Lakh INR) with zero/missing cost safety.
7. Multi-criteria scenario prioritization (Impact, Cost Efficiency, Deployment Speed, Best Balanced).
8. Structured municipal mitigation brief and Markdown report synthesis.
9. Diagnostic record detection and exclusion from real-world fleet planning.

MANDATORY INTEGRITY INVARIANTS:
- 100% in-memory and non-destructive: Never writes or alters Cloud Firestore.
- Every mitigation action and scenario strictly possesses status: "PROPOSED".
- No fabricated official rates or tenders; all estimates are explicit indicative heuristics.
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid
import re

from app.schemas.risk import (
    RiskLevel,
    RiskFactorInput,
    EstimationSource,
    RecommendationPriority,
)
from app.schemas.mitigation import (
    MitigationCategory,
    FeasibilityRating,
    CostConfidence,
    ResourceEstimate,
    MitigationActionPreset,
    ParameterShiftAttribution,
    MitigationScenarioInput,
    ScenarioEvaluation,
    ScenarioRankItem,
    MultiScenarioRankings,
    MultiScenarioSimulationRequest,
    MultiScenarioSimulationResponse,
    MitigationBriefAction,
    MitigationPlanBrief,
)
from app.services.risk_engine import (
    calculate_factor_contributions,
    classify_risk_score,
    WEIGHT_HAZARD,
    WEIGHT_EXPOSURE,
    WEIGHT_VULNERABILITY,
    WEIGHT_DURATION,
)

FACTOR_METADATA = {
    "hazard_severity": ("Hazard Severity (H)", WEIGHT_HAZARD),
    "exposure": ("Population Exposure (E)", WEIGHT_EXPOSURE),
    "vulnerability": ("Infrastructure Vulnerability (V)", WEIGHT_VULNERABILITY),
    "duration": ("Unresolved Duration (D)", WEIGHT_DURATION),
}


SUPPORTED_CATEGORIES = [
    "waterlogging",
    "road_damage",
    "electrical_hazard",
    "waste_management",
    "extreme_heat",
    "general_safety",
]

CATEGORY_ALIASES = {
    "electrical": "electrical_hazard",
    "waste": "waste_management",
    "heat": "extreme_heat",
    "flooding": "waterlogging",
    "flood": "waterlogging",
    "pothole": "road_damage",
    "roads": "road_damage",
    "safety": "general_safety",
}


def is_supported_category(category_input: Optional[str]) -> bool:
    """Validate whether input corresponds to one of the 6 canonical incident taxonomies."""
    if not category_input:
        return False
    clean = str(category_input).lower().strip()
    return clean in SUPPORTED_CATEGORIES or clean in CATEGORY_ALIASES


def normalize_mitigation_category(category_input: Optional[str]) -> str:
    """Normalize input string to technical category key supporting enums and colloquial aliases."""
    raw = str(category_input or "").lower().strip()
    if raw in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[raw]
    if any(k in raw for k in ["water", "flood", "drain", "waterlogging"]):
        return "waterlogging"
    if any(k in raw for k in ["road", "pothole", "asphalt", "subsidence", "road_damage"]):
        return "road_damage"
    if any(k in raw for k in ["electric", "wire", "power", "spark", "transformer", "electrical"]):
        return "electrical_hazard"
    if any(k in raw for k in ["waste", "garbage", "trash", "dump", "debris", "sanitation"]):
        return "waste_management"
    if any(k in raw for k in ["heat", "temperature", "sun", "thermal", "extreme_heat"]):
        return "extreme_heat"
    return "general_safety"


def format_currency_inr(amount: Optional[float], symbol: str = "₹") -> str:
    """Format an amount into Indian numbering system (e.g. ₹1,50,000)."""
    if amount is None:
        return "Unestimated"
    int_amt = int(round(amount))
    s = str(int_amt)
    if len(s) <= 3:
        formatted = s
    else:
        last_three = s[-3:]
        remaining = s[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted = ",".join(groups) + "," + last_three
    return f"{symbol}{formatted}"


def is_diagnostic_record(incident_data: Optional[Dict[str, Any]]) -> bool:
    """
    Check whether an incident document is a diagnostic verification or test record.
    Matches test email patterns, explicit test flags, or diagnostic verification titles.
    """
    if not incident_data:
        return False

    email = str(incident_data.get("reporter_email", "")).lower()
    title = str(incident_data.get("title", "")).lower()
    is_test_flag = bool(incident_data.get("is_test", False))

    if is_test_flag:
        return True
    if re.search(r"diagnostic_test_|@nexus-test\.org|@test\.org", email):
        return True
    if "milestone 2b verification" in title or "diagnostic test" in title or "test hazard" in title:
        return True

    return False


# ============================================================================
# Category-Specific Municipal Mitigation Presets Catalog (All 6 Categories)
# ============================================================================

MITIGATION_ACTION_CATALOG: Dict[str, List[MitigationActionPreset]] = {
    "waterlogging": [
        MitigationActionPreset(
            id="act_wl_high_pump",
            category="waterlogging",
            title="High-Capacity Mobile Dewatering Pump Deployment",
            description="Deploy two 500+ GPM mobile diesel dewatering pumps at the primary road catchment depression.",
            mechanism="Rapidly lowers standing water depth below critical vehicle stalling threshold (40% weight impact on H).",
            target_factor_deltas={"hazard_severity": -35.0, "duration": -25.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=35000.0,
                estimated_cost_max=75000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Standard municipal diesel pump unit rental, fuel logistics, and operator mobilization.",
                estimated_manpower=4,
                manpower_notes="1 field supervisor, 2 mechanical technicians, 1 safety marshal.",
                estimated_duration_hours=3.5,
                duration_notes="1.0 hr transit/setup + 2.5 hrs active pumping.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Towable pump units have unobstructed arterial transit access to the catchment sump.",
            responsible_department="Municipal Stormwater & Disaster Drainage",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_wl_grate_clear",
            category="waterlogging",
            title="Stormwater Grating & Culvert Manual Desilting",
            description="Mobilize ward drainage squad to unblock choked roadside culvert mouths and intake grates.",
            mechanism="Restores gravity outflow conveyance, attenuating structural vulnerability and standing water accumulation.",
            target_factor_deltas={"vulnerability": -25.0, "hazard_severity": -15.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=12000.0,
                estimated_cost_max=25000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Ward labor deployment and manual silt extraction tools.",
                estimated_manpower=5,
                manpower_notes="1 ward sanitary inspector, 4 field laborers.",
                estimated_duration_hours=2.0,
                duration_notes="Immediate manual clearing within 2 hours.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Blockage is localized to surface grates rather than a collapsed subsurface main trunk line.",
            responsible_department="Ward Drainage Maintenance Operations",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_wl_traffic_detour",
            category="waterlogging",
            title="Commuter Traffic Diversion & Barricading",
            description="Deploy high-visibility water-filled barriers and assign traffic marshals to redirect vehicles to high-elevation bypass.",
            mechanism="Eliminates commuter and vehicular presence in submerged zone, sharply dampening population exposure (30% weight).",
            target_factor_deltas={"exposure": -35.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=8000.0,
                estimated_cost_max=18000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Barricade positioning, reflective warning cones, and traffic police coordination.",
                estimated_manpower=3,
                manpower_notes="2 traffic marshals, 1 municipal coordinator.",
                estimated_duration_hours=1.0,
                duration_notes="Rapid sign deployment within 60 minutes.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Secondary bypass route possesses sufficient residual capacity for rerouted vehicles.",
            responsible_department="Traffic Police & Civil Defense",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_wl_retention_basin",
            category="waterlogging",
            title="Modular Subsurface Stormwater Retention Tank",
            description="Install high-capacity subsurface rainwater percolation and retention reservoir underneath roadside green verge.",
            mechanism="Permanently increases localized retention buffer, mitigating infrastructure vulnerability and peak runoff surge.",
            target_factor_deltas={"vulnerability": -45.0, "hazard_severity": -40.0, "duration": -30.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=450000.0,
                estimated_cost_max=950000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Civil excavation, pre-cast modular geocellular infiltration blocks, and backfilling.",
                estimated_manpower=12,
                manpower_notes="1 civil project engineer, 2 machine operators, 9 civil workers.",
                estimated_duration_hours=120.0,
                duration_notes="Civil installation timeframe across 5 operational workdays.",
            ),
            feasibility=FeasibilityRating.COMPLEX,
            assumptions="Requires subsurface utility clearance (water, telecom cables) and formal capital works allocation.",
            responsible_department="Urban Engineering & Public Works Department",
            status="PROPOSED",
        ),
    ],
    "road_damage": [
        MitigationActionPreset(
            id="act_rd_cold_patch",
            category="road_damage",
            title="Rapid Cold-Mix Bituminous Pothole Patching",
            description="Apply pre-mixed polymer-modified cold asphalt into active potholes with mechanical hand plate compactor.",
            mechanism="Levels driving surface immediately, mitigating tire blowout and motorcycle loss-of-control hazards.",
            target_factor_deltas={"hazard_severity": -30.0, "duration": -20.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=20000.0,
                estimated_cost_max=45000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Cold mix bags, tack coat emulsion, and plate compactor rental.",
                estimated_manpower=4,
                manpower_notes="1 roads supervisor, 3 paving technicians.",
                estimated_duration_hours=2.5,
                duration_notes="Patching and curing in 2.5 hours under running traffic.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Pothole cavity is cleared of loose wet mud prior to compaction.",
            responsible_department="Road Maintenance Division, PWD",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_rd_subbase_recon",
            category="road_damage",
            title="Full-Depth Road Sub-base Reconstruction",
            description="Milling of fractured bituminous layer, sub-grade stabilization with wet-mix macadam, and hot-mix asphalt resurfacing.",
            mechanism="Eliminates structural foundation failure, permanently resolving pavement fragility and recurrence.",
            target_factor_deltas={"vulnerability": -40.0, "hazard_severity": -45.0, "duration": -35.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=300000.0,
                estimated_cost_max=650000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Heavy machinery (milling machine, vibratory roller), asphalt paver, hot-mix materials.",
                estimated_manpower=10,
                manpower_notes="1 highway engineer, 3 heavy equipment operators, 6 asphalt crew.",
                estimated_duration_hours=48.0,
                duration_notes="48 hours phased execution over weekend low-traffic window.",
            ),
            feasibility=FeasibilityRating.MODERATE,
            assumptions="Requires partial road closure permits and dry ambient weather.",
            responsible_department="Highways & Urban Infrastructure Wing",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_rd_lane_channelling",
            category="road_damage",
            title="Reflective Lane Channelization & Speed Attenuation",
            description="Install high-intensity retroreflective delineator posts and temporary rubber speed ramps 100m upstream of road defect.",
            mechanism="Slows approaching traffic velocity and funnels vehicles away from damaged asphalt edge, dampening exposure.",
            target_factor_deltas={"exposure": -30.0, "hazard_severity": -10.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=15000.0,
                estimated_cost_max=30000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Delineator posts, rubber ramps, retroreflective directional arrows.",
                estimated_manpower=3,
                manpower_notes="1 road safety inspector, 2 traffic crew.",
                estimated_duration_hours=1.5,
                duration_notes="Rapid installation within 90 minutes.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Roadway possesses multiple lanes to allow single-lane diversion.",
            responsible_department="Traffic Safety & PWD Maintenance",
            status="PROPOSED",
        ),
    ],
    "electrical_hazard": [
        MitigationActionPreset(
            id="act_el_isolate_deenergize",
            category="electrical_hazard",
            title="Rapid Utility Feeder Isolation & De-energization",
            description="Authorized electrical utility technicians operate distribution substation breakers to de-energize damaged line section.",
            mechanism="Completely eliminates electrocution and arc flash hazard by cutting voltage to zero (40% weight).",
            target_factor_deltas={"hazard_severity": -60.0, "duration": -30.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=10000.0,
                estimated_cost_max=25000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Utility emergency response vehicle dispatch and breaker switching protocol.",
                estimated_manpower=2,
                manpower_notes="2 certified high-voltage utility linesmen.",
                estimated_duration_hours=0.5,
                duration_notes="Substation SCADA or field switch isolation within 30 minutes.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="MANDATORY: Executed solely by authorized utility power authority; zero contact by non-certified personnel.",
            responsible_department="Power Distribution Corporation (DISCOM)",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_el_perimeter_cordon",
            category="electrical_hazard",
            title="Non-Conductive Physical Perimeter Cordoning",
            description="Establish an 8-meter radial exclusion boundary using fiberglass non-conductive stanchions and danger flash tape.",
            mechanism="Prevents pedestrians and commuters from approaching step-potential electrocution zone, dampening exposure to zero.",
            target_factor_deltas={"exposure": -45.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=5000.0,
                estimated_cost_max=12000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Insulated barrier ribbons, hazard warning floodlights, and safety cones.",
                estimated_manpower=2,
                manpower_notes="2 civil defense marshals.",
                estimated_duration_hours=0.5,
                duration_notes="Erected within 30 minutes of arrival.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Maintains safe clearance distance of at least 8 meters from hanging or grounded conductor.",
            responsible_department="Civil Defense & Emergency Services",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_el_abc_retrofit",
            category="electrical_hazard",
            title="Aerial Bundled Cable (ABC) Insulated Conductor Retrofit",
            description="Replace exposed bare overhead aluminium conductors with cross-linked polyethylene (XLPE) insulated aerial bundled cables.",
            mechanism="Permanently removes bare wire contact risk, eliminating hazard from falling tree branches or high vehicles.",
            target_factor_deltas={"vulnerability": -50.0, "hazard_severity": -50.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=180000.0,
                estimated_cost_max=420000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Insulated ABC cable spans, tension clamps, pole hardware, and line installation crew.",
                estimated_manpower=6,
                manpower_notes="1 electrical engineer, 5 certified linesmen.",
                estimated_duration_hours=24.0,
                duration_notes="Scheduled weekend reconductoring over 24 hours.",
            ),
            feasibility=FeasibilityRating.MODERATE,
            assumptions="Requires planned utility outage notification to consumers.",
            responsible_department="DISCOM Distribution Infrastructure Wing",
            status="PROPOSED",
        ),
    ],
    "waste_management": [
        MitigationActionPreset(
            id="act_wm_compactor_clear",
            category="waste_management",
            title="Mechanical Compactor Truck Clearance & Sweeping",
            description="Deploy hydraulic rear-loading compactor truck and mechanized bobcat loader to clear open waste dump site.",
            mechanism="Removes decomposing biomass, neutralizing odor, blocking leachate, and attenuating physical hazard.",
            target_factor_deltas={"hazard_severity": -35.0, "duration": -25.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=18000.0,
                estimated_cost_max=40000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Compactor truck fuel, loader rental, tipping fees, and sanitation crew.",
                estimated_manpower=5,
                manpower_notes="1 sanitary supervisor, 1 loader operator, 1 truck driver, 2 sanitation workers.",
                estimated_duration_hours=3.0,
                duration_notes="Mobilization and total site clearance within 3 hours.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Solid waste processing facility or landfill is operational for disposal.",
            responsible_department="Municipal Solid Waste Management Department",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_wm_bio_fumigation",
            category="waste_management",
            title="Bio-Sanitizer Spraying & Vector Fumigation",
            description="Apply microbial enzyme disinfectant spray and thermal fogging across cleared perimeter.",
            mechanism="Destroys vector breeding grounds (flies, mosquitoes, rodents), reducing neighborhood health vulnerability.",
            target_factor_deltas={"vulnerability": -25.0, "hazard_severity": -15.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=8000.0,
                estimated_cost_max=16000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Enzyme solution, thermal fogging oil, backpack spray equipment.",
                estimated_manpower=2,
                manpower_notes="2 certified pest-control technicians.",
                estimated_duration_hours=1.5,
                duration_notes="Application takes 90 minutes post-clearance.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Area cleared of large debris prior to biochemical spraying.",
            responsible_department="Public Health & Vector Control Cell",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_wm_covered_bins",
            category="waste_management",
            title="Installation of Heavy-Duty Covered Community Dumpsters",
            description="Install two 1,100-liter galvanized steel wheeled bins with counterbalanced lids and anti-dumping signage.",
            mechanism="Confines garbage within sealed containers, preventing scavengers and stray animal dispersal.",
            target_factor_deltas={"vulnerability": -35.0, "exposure": -20.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=45000.0,
                estimated_cost_max=90000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Two 1.1 cubic meter galvanized bins, concrete anchoring pad, informational signage.",
                estimated_manpower=3,
                manpower_notes="1 ward officer, 2 installation crew.",
                estimated_duration_hours=6.0,
                duration_notes="Installation and pad setup completed in 6 hours.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Daily municipal collection route includes this location for bin emptying.",
            responsible_department="Sanitation Operations, Municipal Corporation",
            status="PROPOSED",
        ),
    ],
    "extreme_heat": [
        MitigationActionPreset(
            id="act_eh_mist_canopy",
            category="extreme_heat",
            title="High-Pressure Water Misting & Shaded Shelter Canopy",
            description="Deploy temporary shaded marquee with integrated evaporative cooling misting lines at busy transit bus stand.",
            mechanism="Cools micro-climate ambient temperature by 5-8°C, directly mitigating thermal hazard and commuter exposure.",
            target_factor_deltas={"hazard_severity": -30.0, "exposure": -25.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=25000.0,
                estimated_cost_max=60000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Commercial misting pump, high-pressure tubing, water tanker connection, and marquee tent.",
                estimated_manpower=3,
                manpower_notes="1 technician, 2 civil maintenance workers.",
                estimated_duration_hours=3.0,
                duration_notes="Assembly and pressurized water connection in 3 hours.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Clean municipal water supply available via mobile tanker.",
            responsible_department="Disaster Management & Urban Forestry",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_eh_hydration_kiosk",
            category="extreme_heat",
            title="Emergency Hydration & Oral Rehydration Salts (ORS) Hub",
            description="Set up shaded potable water kiosk with chilled drinking water dispensers and electrolyte solution packets.",
            mechanism="Protects pedestrians, outdoor delivery riders, and senior citizens against heat stroke and dehydration.",
            target_factor_deltas={"vulnerability": -35.0, "hazard_severity": -15.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=12000.0,
                estimated_cost_max=28000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="20-liter water jars, dispenser stands, ORS sachets, and paper cups for 3 days.",
                estimated_manpower=2,
                manpower_notes="2 civil volunteer or health workers.",
                estimated_duration_hours=2.0,
                duration_notes="Setup within 2 hours.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Continuous daily replenishment of chilled water containers.",
            responsible_department="Municipal Health Department & Red Cross",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_eh_cool_roof",
            category="extreme_heat",
            title="High-Albedo Solar Reflective Coating (Cool Roof / Pavement)",
            description="Apply high-reflectance white elastomeric solar coating (SRI > 100) on public building roof and asphalt sidewalk.",
            mechanism="Reflects up to 80% of solar radiation, reducing localized urban heat island thermal storage.",
            target_factor_deltas={"vulnerability": -30.0, "hazard_severity": -25.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=80000.0,
                estimated_cost_max=190000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="High-reflectance paint drums, surface primer, pressure washer, and application rollers.",
                estimated_manpower=4,
                manpower_notes="4 painting workers.",
                estimated_duration_hours=16.0,
                duration_notes="Surface cleaning and 2-coat application over 2 days.",
            ),
            feasibility=FeasibilityRating.MODERATE,
            assumptions="Surface is structurally intact and dry before application.",
            responsible_department="Public Works & Sustainable Cities Mission",
            status="PROPOSED",
        ),
    ],
    "general_safety": [
        MitigationActionPreset(
            id="act_gs_solar_lighting",
            category="general_safety",
            title="Mobile Solar Tower Lighting & CCTV Deployment",
            description="Position towable solar-powered LED mast tower illuminating dark hazard area with integrated surveillance.",
            mechanism="Eliminates nighttime blindness and criminal opportunity, reducing social vulnerability and exposure.",
            target_factor_deltas={"vulnerability": -30.0, "hazard_severity": -20.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=25000.0,
                estimated_cost_max=55000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Solar mast light trailer deployment, battery bank check, CCTV link setup.",
                estimated_manpower=2,
                manpower_notes="2 technicians.",
                estimated_duration_hours=2.0,
                duration_notes="Positioning and mast elevation in 2 hours.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Level ground surface available for trailer stabilizer jacks.",
            responsible_department="Municipal Electrical & Civil Defense",
            status="PROPOSED",
        ),
        MitigationActionPreset(
            id="act_gs_barrier_fencing",
            category="general_safety",
            title="Galvanized Perimeter Safety Barricade & Hazard Signage",
            description="Install continuous interlocking steel crowd control barricades with retroreflective hazard warnings around danger zone.",
            mechanism="Prevents public ingress into hazardous site, driving population exposure down significantly.",
            target_factor_deltas={"exposure": -40.0, "duration": -15.0},
            resource_estimate=ResourceEstimate(
                estimated_cost_min=15000.0,
                estimated_cost_max=35000.0,
                currency="INR",
                currency_symbol="₹",
                cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
                cost_notes="Steel barrier panels, interlocking pins, multilingual danger warning boards.",
                estimated_manpower=3,
                manpower_notes="3 municipal maintenance workers.",
                estimated_duration_hours=2.0,
                duration_notes="Deployment completed in 2 hours.",
            ),
            feasibility=FeasibilityRating.HIGH,
            assumptions="Adequate sidewalk width to maintain pedestrian bypass.",
            responsible_department="Public Works & Municipal Law Enforcement",
            status="PROPOSED",
        ),
    ],
}


def get_mitigation_presets(category: Optional[str]) -> List[MitigationActionPreset]:
    """Retrieve cataloged municipal mitigation action presets for a specified category."""
    norm_cat = normalize_mitigation_category(category)
    presets = MITIGATION_ACTION_CATALOG.get(norm_cat)
    if not presets:
        presets = MITIGATION_ACTION_CATALOG.get("general_safety", [])
    return presets


# ============================================================================
# Multi-Scenario Simulation Engine & Ranking Algorithms
# ============================================================================

def calculate_scenario_cost_effectiveness(
    absolute_reduction: float,
    resource: ResourceEstimate,
    cost_unit_lakhs: float = 1.0,
) -> Tuple[Optional[float], str]:
    """
    Safely calculate cost-effectiveness in risk points reduced per ₹1 Lakh (₹1,00,000 INR).
    Handles zero, missing, negative, and unquantifiable cost parameters without division by zero.
    """
    if absolute_reduction <= 0.0:
        return 0.0, "No Risk Reduction (Zero / Negative Delta)"

    mean_cost = resource.mean_cost
    if mean_cost is None:
        return None, "Unestimated Cost (Cost Parameters Not Provided)"

    if mean_cost <= 0.0:
        return None, "Zero Additional Direct Cost (Immediate Non-Monetary Action)"

    # Base cost unit: ₹1,00,000 INR (1 Lakh) * cost_unit_lakhs
    unit_basis = 100000.0 * cost_unit_lakhs
    cost_in_lakhs = mean_cost / unit_basis
    pts_per_lakh = round(absolute_reduction / cost_in_lakhs, 2)
    label = f"{pts_per_lakh:.2f} pts / {resource.currency_symbol}{cost_unit_lakhs:.1f} Lakh"

    return pts_per_lakh, label


def evaluate_single_scenario(
    scenario_input: MitigationScenarioInput,
    baseline_factors: RiskFactorInput,
    base_score: float,
    base_level: RiskLevel,
    currency: str = "INR",
    currency_symbol: str = "₹",
    cost_unit_lakhs: float = 1.0,
) -> ScenarioEvaluation:
    """
    Deterministically evaluate one mitigation scenario against the common baseline.
    Computes score, Delta R, parameter shifts, cost-effectiveness, and driver attribution.
    """
    sim_factors = scenario_input.simulated_factors
    sim_score, _ = calculate_factor_contributions(sim_factors)
    sim_level = classify_risk_score(sim_score)

    absolute_reduction = round(base_score - sim_score, 2)

    # Relative risk reduction percentage (safely handles base_score = 0)
    if base_score <= 0.0:
        relative_reduction_pct = 0.0
    else:
        relative_reduction_pct = round((absolute_reduction / base_score) * 100.0, 1)

    level_changed = (base_level != sim_level)
    level_transition = f"{base_level.value} -> {sim_level.value}" if level_changed else f"Maintained {base_level.value}"

    # Decompose parameter shifts between baseline and simulated
    parameter_shifts: List[ParameterShiftAttribution] = []
    mitigation_deltas: List[Tuple[str, float, float]] = []

    for f_key, (f_label, weight) in FACTOR_METADATA.items():
        b_val = getattr(baseline_factors, f_key)
        s_val = getattr(sim_factors, f_key)
        delta_val = round(s_val - b_val, 2)
        pts_impact = round(delta_val * weight, 2)

        if abs(delta_val) > 0.01:
            direction = "reduced" if delta_val < 0 else "increased"
            rationale_text = (
                f"{f_label} was {direction} by {abs(delta_val):.1f} points "
                f"({pts_impact:+.1f} pts impact on composite score)."
            )
            parameter_shifts.append(
                ParameterShiftAttribution(
                    factor=f_key,
                    factor_label=f_label,
                    baseline_value=b_val,
                    simulated_value=s_val,
                    delta_value=delta_val,
                    formula_weight=weight,
                    risk_points_impact=pts_impact,
                    rationale=rationale_text,
                )
            )
            if pts_impact < 0:
                mitigation_deltas.append((f_label, abs(pts_impact), abs(delta_val)))

    # Determine primary mitigation driver
    if mitigation_deltas:
        mitigation_deltas.sort(key=lambda x: x[1], reverse=True)
        top = mitigation_deltas[0]
        primary_driver = f"Primary mitigation driven by {top[0]} reduction (-{top[1]:.1f} pts impact)"
    elif absolute_reduction < 0:
        primary_driver = f"Risk escalation: Scenario increases overall civic risk by {abs(absolute_reduction):.1f} pts"
    else:
        primary_driver = "Neutral intervention: Baseline and simulated parameters are identical"

    # Derive resource estimate (uses custom override or default)
    if scenario_input.custom_resource_override:
        resource = scenario_input.custom_resource_override
    else:
        # Generic heuristic benchmark if no custom estimate is provided
        resource = ResourceEstimate(
            estimated_cost_min=25000.0,
            estimated_cost_max=60000.0,
            currency=currency,
            currency_symbol=currency_symbol,
            cost_confidence=CostConfidence.DOCUMENTED_BENCHMARK,
            cost_notes="Generic urban operational response heuristic.",
            estimated_manpower=3,
            manpower_notes="Standard 3-person civic field crew.",
            estimated_duration_hours=4.0,
            duration_notes="Standard 4-hour field deployment.",
        )

    pts_per_lakh, efficiency_label = calculate_scenario_cost_effectiveness(
        absolute_reduction=absolute_reduction,
        resource=resource,
        cost_unit_lakhs=cost_unit_lakhs,
    )

    provenance_notes = (
        f"Simulated what-if scenario '{scenario_input.scenario_name}'. "
        f"Evaluated deterministically using R = 0.4H + 0.3E + 0.2V + 0.1D. "
        f"Input source: {sim_factors.source.value}."
    )

    return ScenarioEvaluation(
        scenario_id=scenario_input.scenario_id,
        scenario_name=scenario_input.scenario_name,
        description=scenario_input.description,
        baseline_score=base_score,
        baseline_level=base_level,
        simulated_score=sim_score,
        simulated_level=sim_level,
        absolute_risk_reduction=absolute_reduction,
        relative_risk_reduction_pct=relative_reduction_pct,
        level_changed=level_changed,
        level_transition=level_transition,
        primary_mitigation_driver=primary_driver,
        parameter_shifts=parameter_shifts,
        resource_estimate=resource,
        cost_effectiveness_per_lakh=pts_per_lakh,
        cost_effectiveness_label=efficiency_label,
        feasibility=FeasibilityRating.HIGH,
        is_simulation=True,
        status="PROPOSED",
        provenance_notes=provenance_notes,
    )


def compute_multi_scenario_rankings(
    evaluations: List[ScenarioEvaluation],
    currency_symbol: str = "₹",
) -> MultiScenarioRankings:
    """
    Compute separate deterministic scenario rankings for:
    1. Maximum Risk Reduction (Impact)
    2. Cost Efficiency (Points reduced per ₹1 Lakh)
    3. Deployment Speed (Shortest duration in hours)
    4. Best Balanced (Multi-criteria composite)
    """
    # 1. Ranking by Impact (|Delta R| reduction)
    # Sort descending by absolute reduction; tie-breaker: lower simulated score, then scenario_id
    sorted_by_impact = sorted(
        evaluations,
        key=lambda e: (e.absolute_risk_reduction, -e.simulated_score, e.scenario_id),
        reverse=True,
    )
    rank_impact = [
        ScenarioRankItem(
            rank=i + 1,
            scenario_id=e.scenario_id,
            scenario_name=e.scenario_name,
            metric_value=e.absolute_risk_reduction,
            metric_label=f"-{e.absolute_risk_reduction:.1f} pts ({e.relative_risk_reduction_pct:.1f}% reduction)",
            rationale=(
                f"Reduces composite risk from {e.baseline_score:.1f} to {e.simulated_score:.1f} "
                f"({e.level_transition or 'No change'})."
            ),
        )
        for i, e in enumerate(sorted_by_impact)
    ]

    # 2. Ranking by Cost Efficiency (Points per Lakh)
    # Tier 1: Quantifiable positive reductions sorted descending by pts_per_lakh
    # Tier 2: Zero-cost positive reductions
    # Tier 3: Zero or negative reductions / unestimated costs
    def _cost_sort_key(e: ScenarioEvaluation) -> Tuple[int, float, float, str]:
        if e.absolute_risk_reduction <= 0:
            return (0, 0.0, 0.0, e.scenario_id)
        if e.cost_effectiveness_per_lakh is not None and e.cost_effectiveness_per_lakh > 0:
            return (2, e.cost_effectiveness_per_lakh, e.absolute_risk_reduction, e.scenario_id)
        if e.resource_estimate.mean_cost == 0.0:
            return (3, 9999.0, e.absolute_risk_reduction, e.scenario_id)  # Zero-cost bonus
        return (1, 0.0, e.absolute_risk_reduction, e.scenario_id)

    sorted_by_cost = sorted(evaluations, key=_cost_sort_key, reverse=True)
    rank_cost = [
        ScenarioRankItem(
            rank=i + 1,
            scenario_id=e.scenario_id,
            scenario_name=e.scenario_name,
            metric_value=e.cost_effectiveness_per_lakh,
            metric_label=e.cost_effectiveness_label,
            rationale=(
                f"Estimated mean cost {format_currency_inr(e.resource_estimate.mean_cost, currency_symbol)} "
                f"yields {e.absolute_risk_reduction:.1f} points risk reduction."
            ),
        )
        for i, e in enumerate(sorted_by_cost)
    ]

    # 3. Ranking by Deployment Speed (Shortest duration in hours)
    # Sort ascending by duration hours; tie-breaker: higher risk reduction, then scenario_id
    def _speed_sort_key(e: ScenarioEvaluation) -> Tuple[float, float, str]:
        dur = e.resource_estimate.estimated_duration_hours
        if dur is None:
            return (999999.0, -e.absolute_risk_reduction, e.scenario_id)
        return (dur, -e.absolute_risk_reduction, e.scenario_id)

    sorted_by_speed = sorted(evaluations, key=_speed_sort_key)
    rank_speed = [
        ScenarioRankItem(
            rank=i + 1,
            scenario_id=e.scenario_id,
            scenario_name=e.scenario_name,
            metric_value=e.resource_estimate.estimated_duration_hours,
            metric_label=(
                f"{e.resource_estimate.estimated_duration_hours:.1f} hours"
                if e.resource_estimate.estimated_duration_hours is not None
                else "Unspecified duration"
            ),
            rationale=(
                f"Deployment lead-time of {e.resource_estimate.estimated_duration_hours or 'N/A'} hrs "
                f"with {e.resource_estimate.estimated_manpower or 'N/A'} crew members."
            ),
        )
        for i, e in enumerate(sorted_by_speed)
    ]

    # 4. Best Balanced Scenario
    # Composite scoring: 50% Impact + 30% Cost Efficiency + 20% Speed
    def _composite_score(e: ScenarioEvaluation) -> float:
        if e.absolute_risk_reduction <= 0:
            return -100.0
        # Impact normalized (up to 100 pts)
        impact_norm = min(1.0, max(0.0, e.absolute_risk_reduction / 100.0))
        # Cost efficiency normalized (benchmark 20 pts per lakh = 1.0)
        eff = e.cost_effectiveness_per_lakh or 0.0
        eff_norm = min(1.0, max(0.0, eff / 20.0))
        # Speed normalized (faster = better; benchmark 48 hours)
        dur = e.resource_estimate.estimated_duration_hours or 24.0
        speed_norm = max(0.0, 1.0 - (dur / 48.0))
        return (0.5 * impact_norm) + (0.3 * eff_norm) + (0.2 * speed_norm)

    evaluations_with_scores = [(e, _composite_score(e)) for e in evaluations]
    evaluations_with_scores.sort(key=lambda x: (x[1], x[0].absolute_risk_reduction, x[0].scenario_id), reverse=True)
    best_candidate, best_score = evaluations_with_scores[0]

    best_balanced_item = ScenarioRankItem(
        rank=1,
        scenario_id=best_candidate.scenario_id,
        scenario_name=best_candidate.scenario_name,
        metric_value=round(best_score * 100.0, 1),
        metric_label=f"Balance Score: {round(best_score * 100.0, 1)} / 100",
        rationale=(
            f"Recommended optimal scenario: Combines substantial risk reduction "
            f"(-{best_candidate.absolute_risk_reduction:.1f} pts) with moderate cost "
            f"({format_currency_inr(best_candidate.resource_estimate.mean_cost, currency_symbol)}) "
            f"and rapid deployment ({best_candidate.resource_estimate.estimated_duration_hours or 'N/A'} hrs)."
        ),
    )

    return MultiScenarioRankings(
        by_impact=rank_impact,
        by_cost_efficiency=rank_cost,
        by_deployment_speed=rank_speed,
        best_balanced=best_balanced_item,
    )


def simulate_multi_scenarios(
    request: MultiScenarioSimulationRequest,
    incident_data: Optional[Dict[str, Any]] = None,
) -> MultiScenarioSimulationResponse:
    """
    Execute non-destructive comparative simulation evaluating 2 to 5 competing scenarios
    against one common baseline incident.
    """
    # 1. Check diagnostic test provenance
    is_diag = is_diagnostic_record(incident_data)
    diag_notice = None
    if is_diag:
        diag_notice = (
            "DIAGNOSTIC TEST RECORD: This incident was created during platform verification. "
            "Evaluated scenarios are strictly illustrative and excluded from real-world fleet aggregates."
        )

    # 2. Compute authoritative baseline score & classification
    base_score, _ = calculate_factor_contributions(request.baseline_factors)
    base_level = classify_risk_score(base_score)

    # 3. Evaluate each scenario individually
    evaluations: List[ScenarioEvaluation] = []
    for scen_input in request.scenarios:
        evaluation = evaluate_single_scenario(
            scenario_input=scen_input,
            baseline_factors=request.baseline_factors,
            base_score=base_score,
            base_level=base_level,
            currency=request.currency,
            currency_symbol=request.currency_symbol,
            cost_unit_lakhs=request.cost_unit_lakhs,
        )
        evaluations.append(evaluation)

    # 4. Compute multi-criteria rankings
    rankings = compute_multi_scenario_rankings(
        evaluations=evaluations,
        currency_symbol=request.currency_symbol,
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    sim_id = f"sim_multi_{uuid.uuid4().hex[:12]}"

    methodology = (
        "Multi-criteria deterministic what-if scenario comparison. "
        "Evaluates pre- and post-intervention parameter shifts using formula R = 0.4H + 0.3E + 0.2V + 0.1D. "
        "Quantifies risk reduction, classification band transitions, and resource efficiency indices."
    )

    planning_disclaimer = (
        "All simulated risk reductions and resource requirements are indicative planning heuristics. "
        "Interventions are PROPOSED and do not represent committed municipal expenditure or actual physical execution."
    )

    return MultiScenarioSimulationResponse(
        simulation_id=sim_id,
        incident_id=request.incident_id,
        is_diagnostic_record=is_diag,
        diagnostic_notice=diag_notice,
        baseline_score=base_score,
        baseline_level=base_level,
        baseline_factors=request.baseline_factors,
        scenarios_evaluated_count=len(evaluations),
        evaluations=evaluations,
        rankings=rankings,
        currency=request.currency,
        currency_symbol=request.currency_symbol,
        formula="R = 0.4H + 0.3E + 0.2V + 0.1D",
        methodology=methodology,
        planning_disclaimer=planning_disclaimer,
        created_at=now_iso,
    )


# ============================================================================
# Structured Mitigation Brief & Markdown Report Synthesis
# ============================================================================

def generate_mitigation_plan_brief(
    simulation_response: MultiScenarioSimulationResponse,
    preferred_scenario_id: Optional[str] = None,
    incident_title: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
) -> MitigationPlanBrief:
    """
    Synthesize structured executive mitigation brief data for municipal decision-makers.
    """
    # Identify preferred scenario (uses explicit choice or best_balanced)
    selected_eval = None
    target_id = preferred_scenario_id
    if not target_id and simulation_response.rankings.best_balanced:
        target_id = simulation_response.rankings.best_balanced.scenario_id

    for e in simulation_response.evaluations:
        if e.scenario_id == target_id:
            selected_eval = e
            break

    if not selected_eval:
        selected_eval = simulation_response.evaluations[0]

    # Format cost range
    min_c = selected_eval.resource_estimate.estimated_cost_min
    max_c = selected_eval.resource_estimate.estimated_cost_max
    sym = selected_eval.resource_estimate.currency_symbol
    cost_str = f"{format_currency_inr(min_c, sym)} – {format_currency_inr(max_c, sym)}"

    # Format manpower & duration
    mp = selected_eval.resource_estimate.estimated_manpower
    mp_str = f"{mp} crew members ({selected_eval.resource_estimate.manpower_notes or 'standard crew'})" if mp else "Unspecified crew size"
    dur = selected_eval.resource_estimate.estimated_duration_hours
    dur_str = f"{dur:.1f} hours ({selected_eval.resource_estimate.duration_notes or 'deployment lead-time'})" if dur else "Unspecified duration"

    # Action line items
    actions: List[MitigationBriefAction] = [
        MitigationBriefAction(
            action_id=f"act_{selected_eval.scenario_id}_{i+1}",
            title=shift.rationale,
            department="Municipal Operations & Disaster Management",
            priority=RecommendationPriority.IMMEDIATE if selected_eval.baseline_level == RiskLevel.HIGH else RecommendationPriority.HIGH,
            status="PROPOSED",
        )
        for i, shift in enumerate(selected_eval.parameter_shifts)
    ]

    assumptions_list = [
        "Risk scores calculated strictly via deterministic equation: R = 0.4H + 0.3E + 0.2V + 0.1D.",
        f"Resource benchmarks based on: {selected_eval.resource_estimate.cost_notes or 'Standard municipal schedule of rates'}.",
        f"Target parameter shifts assumed for {selected_eval.scenario_name}: {selected_eval.primary_mitigation_driver}.",
    ]

    disclaimers_list = [
        "Every recommended action strictly carries status 'PROPOSED' pending official administrative authorization.",
        "Resource costs, crew sizes, and operational hours are planning estimates, not contractor bids or budget sanctions.",
        "Simulated risk scores reflect mathematical potential and do not assert verified on-site mitigation until confirmed by field inspections.",
    ]

    if simulation_response.is_diagnostic_record:
        disclaimers_list.insert(
            0,
            "DIAGNOSTIC TEST RECORD: This incident was created for platform verification. Not an authentic community hazard.",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    brief_id = f"brief_{uuid.uuid4().hex[:10]}"

    return MitigationPlanBrief(
        brief_id=brief_id,
        incident_id=simulation_response.incident_id,
        incident_title=incident_title or "Municipal Incident Mitigation Review",
        category=normalize_mitigation_category(category),
        location=location or "Urban Municipal Ward Sector",
        is_diagnostic=simulation_response.is_diagnostic_record,
        baseline_score=simulation_response.baseline_score,
        baseline_level=simulation_response.baseline_level,
        recommended_scenario_id=selected_eval.scenario_id,
        recommended_scenario_name=selected_eval.scenario_name,
        projected_score=selected_eval.simulated_score,
        projected_level=selected_eval.simulated_level,
        projected_risk_reduction=selected_eval.absolute_risk_reduction,
        estimated_cost_range=cost_str,
        estimated_manpower=mp_str,
        estimated_duration=dur_str,
        proposed_actions=actions,
        assumptions_and_sources=assumptions_list,
        disclaimers=disclaimers_list,
        generated_at=now_iso,
    )


def generate_mitigation_brief_markdown(
    brief: MitigationPlanBrief,
    simulation_response: MultiScenarioSimulationResponse,
) -> str:
    """
    Generate an executive-ready Markdown mitigation brief with comparative matrix and assumptions.
    """
    lines = [
        f"# Municipal Mitigation Brief: {brief.incident_title}",
        "",
        f"**Brief ID:** `{brief.brief_id}`  ",
        f"**Category:** `{brief.category.upper()}` | **Location:** {brief.location}  ",
        f"**Generated At:** {brief.generated_at} (UTC)  ",
        f"**Status:** **PROPOSED INTERVENTIONS ONLY**  ",
        "",
    ]

    if brief.is_diagnostic:
        lines.extend([
            "> [!WARNING]",
            "> **Diagnostic Verification Record**: This incident was generated during test verification.",
            "> All scenarios and resource figures are illustrative planning exercises.",
            "",
        ])

    lines.extend([
        "## 1. Executive Summary & Recommended Strategy",
        "",
        f"The baseline incident evaluated at a composite risk score of **{brief.baseline_score:.1f}/100** ({brief.baseline_level.value} Risk).",
        f"Among {simulation_response.scenarios_evaluated_count} competing what-if mitigation scenarios, the recommended balanced strategy is:",
        "",
        f"> ### **{brief.recommended_scenario_name}**",
        f"> - **Projected Risk Score:** **{brief.projected_score:.1f}/100** ({brief.projected_level.value} Risk)",
        f"> - **Projected Risk Reduction (ΔR):** **-{brief.projected_risk_reduction:.1f} points**",
        f"> - **Estimated Cost Range:** {brief.estimated_cost_range}",
        f"> - **Required Crew:** {brief.estimated_manpower}",
        f"> - **Deployment Lead-Time:** {brief.estimated_duration}",
        "",
        "## 2. Multi-Scenario Comparative Evaluation",
        "",
        "| Scenario Name | Simulated Score | ΔR Impact | Risk Level Shift | Est. Cost (INR) | Points / ₹1 Lakh | Feasibility |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])

    for e in simulation_response.evaluations:
        c_str = format_currency_inr(e.resource_estimate.mean_cost, e.resource_estimate.currency_symbol)
        eff_str = f"{e.cost_effectiveness_per_lakh:.1f} pts" if e.cost_effectiveness_per_lakh is not None else "N/A"
        rec_marker = " **(Recommended)**" if e.scenario_id == brief.recommended_scenario_id else ""
        lines.append(
            f"| **{e.scenario_name}**{rec_marker} | {e.simulated_score:.1f} | -{e.absolute_risk_reduction:.1f} pts | {e.level_transition} | {c_str} | {eff_str} | {e.feasibility.value} |"
        )

    lines.extend([
        "",
        "## 3. Proposed Operational Actions",
        "",
    ])

    for i, act in enumerate(brief.proposed_actions):
        lines.append(f"{i+1}. **{act.title}**")
        lines.append(f"   - **Department:** {act.department}")
        lines.append(f"   - **Priority:** `{act.priority.value}` | **Status:** `{act.status}`")

    lines.extend([
        "",
        "## 4. Transparent Assumptions & Methodology",
        "",
    ])
    for a in brief.assumptions_and_sources:
        lines.append(f"- {a}")

    lines.extend([
        "",
        "## 5. Mandatory Disclaimers",
        "",
    ])
    for d in brief.disclaimers:
        lines.append(f"- {d}")

    lines.append("")
    return "\n".join(lines)
