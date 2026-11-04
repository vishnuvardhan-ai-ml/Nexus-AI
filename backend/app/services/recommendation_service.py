"""
NEXUS AI Context-Aware Civic Recommendation Service.

Generates deterministic, actionable civic interventions tailored to:
1. Incident category (waterlogging, road_damage, electrical, waste, extreme_heat, general_safety).
2. Authoritative risk level (LOW, MEDIUM, HIGH) and score.
3. Primary and secondary mathematical risk drivers (H, E, V, D).

MANDATORY RULES:
- Every recommendation strictly possesses status: "PROPOSED". Actions are never claimed completed.
- Electrical hazards enforce non-contact safety boundaries and utility personnel dispatch.
- Recommendations avoid generic boilerplate; they provide concrete operational steps.
- Role-based authorization: Community users can only access their own reported incidents;
  Analysts and Admins have system-wide access.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib
from fastapi import HTTPException, status

from app.schemas.risk import (
    RiskLevel,
    RecommendationPriority,
    RecommendationItem,
    RecommendationListResponse,
)
from app.schemas.user import UserRole, UserPrincipal

# Normalized category keys
VALID_CATEGORIES = [
    "waterlogging",
    "road_damage",
    "electrical",
    "waste",
    "extreme_heat",
    "general_safety",
]


def normalize_category(category_input: str) -> str:
    """Normalize raw category input to recognized technical domain key."""
    clean = str(category_input or "").lower().strip()
    if any(k in clean for k in ["water", "flood", "drain"]):
        return "waterlogging"
    if any(k in clean for k in ["road", "pothole", "asphalt", "traffic"]):
        return "road_damage"
    if any(k in clean for k in ["electric", "wire", "power", "spark", "transformer"]):
        return "electrical"
    if any(k in clean for k in ["waste", "garbage", "trash", "dump", "debris"]):
        return "waste"
    if any(k in clean for k in ["heat", "temperature", "sun", "thermal"]):
        return "extreme_heat"
    return "general_safety"


def generate_recommendation_id(incident_id: Optional[str], index: int, action_text: str) -> str:
    """Deterministic, reproducible ID generation."""
    prefix = f"{incident_id or 'rec'}_{index}"
    h = hashlib.md5(action_text.encode("utf-8")).hexdigest()[:6]
    return f"{prefix}_{h}"


# Action Catalogs indexed by (category, driver, risk_level_bracket)
RECOMMENDATION_MATRIX: Dict[str, Dict[str, Dict[str, Dict[str, str]]]] = {
    "waterlogging": {
        "hazard": {
            "HIGH": {
                "action": "Deploy high-volume dewatering pumps (500+ GPM) at primary collection sump.",
                "priority": RecommendationPriority.IMMEDIATE,
                "rationale": "Physical water depth constitutes the primary risk driver (40% weight), obstructing transit arterial.",
                "suggested_next_step": "Dispatch mobile emergency drainage crew to junction with diesel backup generator.",
                "department": "Municipal Stormwater & Disaster Drainage",
            },
            "MEDIUM": {
                "action": "Clear culvert throat and catch-basin grills of accumulated leaves and silt.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Water ponding is escalating due to localized stormwater intake choke.",
                "suggested_next_step": "Mobilize ward sanitation drain-clearing squad with manual silt extraction tools.",
                "department": "Ward Drainage Operations",
            },
            "LOW": {
                "action": "Schedule pre-monsoon storm sewer desilting and gradient inspection.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Minor standing water baseline requires preventive maintenance to prevent wet-season escalation.",
                "suggested_next_step": "Log drain section for standard quarterly desilting sweep.",
                "department": "Public Works Department",
            },
        },
        "exposure": {
            "HIGH": {
                "action": "Establish traffic diversions around submerged road section and deploy marshals.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "High commuter and vehicular exposure amplifies potential for stalled engines and pedestrian falls.",
                "suggested_next_step": "Coordinate with Traffic Police to post high-water detour signage 200m before hazard zone.",
                "department": "Traffic Police & Civil Defense",
            },
            "MEDIUM": {
                "action": "Erect retroreflective flood hazard warning stanchions along pedestrian sidewalks.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Pedestrians require visual demarcation between footpath boundary and submerged road gutter.",
                "suggested_next_step": "Place 4 illuminated reflective hazard delineator cones along flooded curb margin.",
                "department": "Civic Safety Bureau",
            },
            "LOW": {
                "action": "Monitor pedestrian transit volume during peak precipitation intervals.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Exposure density is restrained; routine pedestrian monitoring is adequate.",
                "suggested_next_step": "Review civic CCTV feed during evening commute.",
                "department": "Municipal Traffic Monitoring Center",
            },
        },
        "vulnerability": {
            "HIGH": {
                "action": "Distribute sandbag barriers to vulnerable ground-floor homes and elder-care facilities.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Structural vulnerability threatens low-elevation dwellings lacking perimeter storm bunds.",
                "suggested_next_step": "Deliver 100 poly-weave sandbags to ward volunteer coordinator for immediate placement.",
                "department": "Civic Disaster Relief & Social Welfare",
            },
            "MEDIUM": {
                "action": "Inspect electrical grounding on submerged street infrastructure.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Submerged civic utilities in vulnerable corridors risk stray currents if moisture seals degrade.",
                "suggested_next_step": "Conduct voltage leak probe on nearest street lighting junction poles.",
                "department": "Municipal Electrical Works",
            },
            "LOW": {
                "action": "Audit neighborhood rainwater harvesting absorption capacity.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Promote local permeable sub-base infiltration to reduce runoff loads.",
                "suggested_next_step": "Share rainwater percolation advisory with resident welfare association.",
                "department": "Urban Planning Bureau",
            },
        },
        "duration": {
            "HIGH": {
                "action": "Escalate prolonged water stagnation to Executive Engineer for heavy suction deployment.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Elapsed ponding duration increases mosquito breeding and road sub-grade saturation.",
                "suggested_next_step": "Contract commercial vacuum suction trucks for rapid standing-water evacuation.",
                "department": "Emergency Public Works Operations",
            },
            "MEDIUM": {
                "action": "Apply anti-larval chemical treatment to persistent roadside standing water.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Unresolved ponding exceeding 48 hours constitutes an active dengue/malaria vector hazard.",
                "suggested_next_step": "Deploy vector-control team to spray Temephos larvicide on standing pools.",
                "department": "Public Health & Vector Control",
            },
            "LOW": {
                "action": "Log natural evaporation and seepage recovery rate.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Ponding duration is within normal post-storm recession window.",
                "suggested_next_step": "Inspect site after 12 hours to confirm full gravity runoff.",
                "department": "Ward Engineering Oversight",
            },
        },
    },
    "road_damage": {
        "hazard": {
            "HIGH": {
                "action": "Execute immediate cold-mix asphalt patching or install heavy steel road plates.",
                "priority": RecommendationPriority.IMMEDIATE,
                "rationale": "Crater void depth (>6 inches) presents acute risk of fatal vehicular turnover and wheel fracture.",
                "suggested_next_step": "Dispatch rapid road response truck with pre-mixed cold asphalt and mechanical tamper.",
                "department": "Highways & Road Maintenance Division",
            },
            "MEDIUM": {
                "action": "Refill road depression with graded crushed aggregate and asphalt tack coat.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Asphalt wear is accelerating under axle load and risks acute sub-base failure.",
                "suggested_next_step": "Schedule aggregate leveling work order within next 24 hours.",
                "department": "Municipal Road Works",
            },
            "LOW": {
                "action": "Mark hairline asphalt fissures for crack-sealing in routine maintenance cycle.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Surface roughness does not present acute vehicular hazard but requires preventative seal.",
                "suggested_next_step": "Include street segment in scheduled bitumen seal-coat registry.",
                "department": "Road Asset Management",
            },
        },
        "exposure": {
            "HIGH": {
                "action": "Erect retroreflective safety barriers and luminous blinkers 50m ahead of road void.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Dense vehicular and two-wheeler volume increases crash probability in unlit conditions.",
                "suggested_next_step": "Place 6 heavy orange traffic barrels and battery-operated amber hazard flasher.",
                "department": "Traffic Management & Signage",
            },
            "MEDIUM": {
                "action": "Deploy warning signage indicating rough road surface ahead.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Alert motorists to reduce speed to 20 km/h along deteriorating segment.",
                "suggested_next_step": "Install temporary 'Caution - Uneven Road' reflective sign board.",
                "department": "Traffic Police Division",
            },
            "LOW": {
                "action": "Monitor peak vehicle speeds across the affected road stretch.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Low traffic density allows standard flow without traffic diversion requirements.",
                "suggested_next_step": "Verify speed limit compliance via speed camera.",
                "department": "Traffic Enforcement",
            },
        },
        "vulnerability": {
            "HIGH": {
                "action": "Investigate underground water/sewer pipe leaks causing structural sub-grade washout.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Subsurface piping voids cause catastrophic asphalt cave-ins under heavy axle loads.",
                "suggested_next_step": "Request municipal water utility conduct ground-penetrating acoustic leak detection.",
                "department": "Water Supply & Sewerage Board",
            },
            "MEDIUM": {
                "action": "Reinforce road shoulder and install concrete perimeter curb.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Unpaved shoulder degradation causes lateral road edge collapse.",
                "suggested_next_step": "Pour quick-setting concrete curb along vulnerable road margin.",
                "department": "Civil Infrastructure Division",
            },
            "LOW": {
                "action": "Audit stormwater runoff gutter slope along curb boundary.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Prevent water accumulation along road shoulder to preserve bitumen binder.",
                "suggested_next_step": "Ensure curb weep holes are clear of dirt.",
                "department": "Ward Public Works",
            },
        },
        "duration": {
            "HIGH": {
                "action": "Issue formal breach notice to maintenance contractor and invoke emergency repair funds.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Damage has persisted past contractual SLA, compounding community transit hazards.",
                "suggested_next_step": "Direct emergency repair team to complete fix and back-charge defaulting contractor.",
                "department": "Municipal Contract & Quality Oversight",
            },
            "MEDIUM": {
                "action": "Escalate open defect ticket to Ward Assistant Engineer for priority scheduling.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Sustained delay threatens further road sub-base deterioration.",
                "suggested_next_step": "Review open grievance status in morning municipal engineer standup.",
                "department": "Civic Grievance Redressal Cell",
            },
            "LOW": {
                "action": "Track asphalt performance in quarterly municipal road inventory.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Duration is within standard non-emergency inspection timeframe.",
                "suggested_next_step": "Maintain log in road asset management database.",
                "department": "Public Works Division",
            },
        },
    },
    "electrical": {
        "hazard": {
            "HIGH": {
                "action": "CRITICAL LIFE SAFETY: Immediately notify power utility emergency dispatch for circuit de-energization. Strictly prohibit public contact and avoid approaching exposed electrical equipment or standing water. Do not treat any fixed distance as universally safe under wet or high-voltage ground gradient conditions; maintain maximal separation and await certified utility personnel.",
                "priority": RecommendationPriority.IMMEDIATE,
                "rationale": "Lethal electrocution and step-potential risk. Ground potential gradients can carry lethal voltage through wet soil and puddles.",
                "suggested_next_step": "Call Electric Utility Emergency Despatch Control Room immediately for verified substation isolation.",
                "department": "State Power Distribution Corporation (DISCOM)",
            },
            "MEDIUM": {
                "action": "De-energize localized street lighting circuit and replace cracked dielectric junction box cover.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Exposed terminal blocks at accessible height present shock hazard during rainfall.",
                "suggested_next_step": "Dispatch authorized utility electrician equipped with 1000V insulated tools and composite latching cover.",
                "department": "Municipal Street Lighting Maintenance",
            },
            "LOW": {
                "action": "Conduct daylight thermal scan and torque check on terminal block connections.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Low-level flickering indicates loose terminal connection without active dielectric breakdown.",
                "suggested_next_step": "Tighten terminal screws and apply anti-corrosive dielectric grease.",
                "department": "Electrical Maintenance Division",
            },
        },
        "exposure": {
            "HIGH": {
                "action": "Deploy civic safety marshals with caution perimeter tape to repel pedestrians from energized zone.",
                "priority": RecommendationPriority.IMMEDIATE,
                "rationale": "High pedestrian density near school/transit stops necessitates physical human barrier until power cut.",
                "suggested_next_step": "Station 2 civil defense personnel at 10-meter perimeter with megaphones warning the public.",
                "department": "City Police & Civil Emergency Corps",
            },
            "MEDIUM": {
                "action": "Cordon off utility pole base with non-conductive plastic caution barricades.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Prevent children or animals from approaching accessible low-hanging wire or unlatched box.",
                "suggested_next_step": "Affix high-voltage danger warning signage with skull icon.",
                "department": "Civic Safety Bureau",
            },
            "LOW": {
                "action": "Check pedestrian clearance height of aerial telecommunication and secondary lines.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Ensure statutory 14-foot overhead clearance is maintained across roadway.",
                "suggested_next_step": "Verify line tension with measuring rod.",
                "department": "Utility Infrastructure Oversight",
            },
        },
        "vulnerability": {
            "HIGH": {
                "action": "Install IP66 weatherproof lockable composite junction enclosures and residual current breakers.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Corroded mild-steel panels allow water ingress and ground faults during wet season.",
                "suggested_next_step": "Retrofit 30mA high-sensitivity earth leakage circuit breaker (ELCB) on circuit.",
                "department": "Electrical Inspectorate & Standards Division",
            },
            "MEDIUM": {
                "action": "Re-stake copper earth electrode and measure soil resistivity.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Defective grounding prevents rapid breaker tripping during electrical fault.",
                "suggested_next_step": "Pour salt-charcoal conditioning mixture into grounding pit to lower ground resistance below 2 ohms.",
                "department": "Electrical Maintenance Cell",
            },
            "LOW": {
                "action": "Annual dielectric insulation resistance testing of distribution transformer bushing.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Preventative verification of grid asset integrity.",
                "suggested_next_step": "Log 1000V Megger insulation reading in substation register.",
                "department": "Power Distribution Utility",
            },
        },
        "duration": {
            "HIGH": {
                "action": "Urgent executive escalation: Unresolved electrical hazard exceeds maximum statutory public safety window.",
                "priority": RecommendationPriority.IMMEDIATE,
                "rationale": "Prolonged exposure of energized electrical hazard compounds probability of fatal incident.",
                "suggested_next_step": "Transmit high-priority dispatch notice directly to Executive Engineer (O&M).",
                "department": "Chief Electrical Inspectorate",
            },
            "MEDIUM": {
                "action": "Re-prioritize pending electrical work orders for feeder line trimming.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Prevent ongoing tree branch contact from chafing conductor insulation.",
                "suggested_next_step": "Schedule bucket-truck tree pruner team for early morning maintenance outage.",
                "department": "Power Utility Forestry Team",
            },
            "LOW": {
                "action": "Review quarterly electrical fault incidence on feeder.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Track minor tripping trends for preventative transformer maintenance.",
                "suggested_next_step": "Analyze SCADA telemetry logs.",
                "department": "Power Grid Telemetry Operations",
            },
        },
    },
    "waste": {
        "hazard": {
            "HIGH": {
                "action": "Deploy front-end hydraulic loaders and enclosed compactor trucks for immediate hazardous waste extraction.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Massive solid waste accumulation creates noxious decomposition gases and acute biological biohazard.",
                "suggested_next_step": "Direct 2 ten-ton compactor trucks to site and transport waste to authorized treatment facility.",
                "department": "Solid Waste Management Division",
            },
            "MEDIUM": {
                "action": "Clear overflowing roadside municipal dumpster and replace damaged collection bin.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Overflowing waste spills into roadway and clogs adjacent stormwater channels.",
                "suggested_next_step": "Dispatch refuse collection compactor for full site clearance within 4 hours.",
                "department": "Ward Sanitation Operations",
            },
            "LOW": {
                "action": "Schedule standard daily dumper-placer pickup cycle.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Dry litter volume is manageable within scheduled collection timetable.",
                "suggested_next_step": "Confirm morning collection truck logged site on GPS route.",
                "department": "Municipal Waste Logistics",
            },
        },
        "exposure": {
            "HIGH": {
                "action": "Spray eco-friendly broad-spectrum disinfectant and larvicide across cleared waste area.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "High residential and market exposure requires immediate neutralization of microbial pathogens and odor.",
                "suggested_next_step": "Mist area with 2% sodium hypochlorite and biological odor-neutralizing enzyme solution.",
                "department": "Public Health & Sanitation Enforcement",
            },
            "MEDIUM": {
                "action": "Erect temporary mesh screening around collection point to contain wind-blown debris.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Prevents plastic bags and lightweight refuse from dispersing across commuter lanes.",
                "suggested_next_step": "Fasten 6-foot geotextile green netting along boundary fence.",
                "department": "Civic Sanitation Bureau",
            },
            "LOW": {
                "action": "Place visible bilingual signage against open roadside dumping.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Reinforce neighborhood compliance with civic disposal bylaws.",
                "suggested_next_step": "Affix metal notice board specifying dumping penalty fines.",
                "department": "Civic Enforcement Cell",
            },
        },
        "vulnerability": {
            "HIGH": {
                "action": "Install physical precast concrete bollards and CCTV surveillance to prevent repeat commercial dumping.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Vulnerable vacant plots attract persistent midnight industrial and debris dumping.",
                "suggested_next_step": "Install 3 concrete barriers blocking vehicle approach and connect solar-powered surveillance camera.",
                "department": "Civic Infrastructure & Smart City Operations",
            },
            "MEDIUM": {
                "action": "Provide additional segregated 240L wheeled bins for dry and wet waste.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Local commercial eateries require dedicated organic waste disposal receptacles.",
                "suggested_next_step": "Distribute 4 color-coded bins to market trade association.",
                "department": "Solid Waste Management Cell",
            },
            "LOW": {
                "action": "Organize door-to-door waste segregation awareness drive.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Foster household source-segregation to reduce open garbage vulnerability.",
                "suggested_next_step": "Conduct community outreach session with Resident Welfare Association.",
                "department": "Community Engagement Division",
            },
        },
        "duration": {
            "HIGH": {
                "action": "Issue formal penalty notice to assigned private sanitation concessionaire for multi-day non-collection.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Extended waste stagnation violates municipal sanitation charters and worsens vector propagation.",
                "suggested_next_step": "Levy contractual liquidated damages and assign secondary contractor.",
                "department": "Municipal Concession & Contract Cell",
            },
            "MEDIUM": {
                "action": "Double daily collection frequency from once to twice daily during peak market hours.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "High waste generation outpaces single daily collection schedule.",
                "suggested_next_step": "Adjust contractor route schedule to add an evening clearance sweep.",
                "department": "Municipal Logistics Division",
            },
            "LOW": {
                "action": "Track sanitation truck GPS logs for route adherence verification.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Ensure timely pickups remain synchronized with generation patterns.",
                "suggested_next_step": "Review weekly telemetry report.",
                "department": "Sanitation Telemetry Center",
            },
        },
    },
    "extreme_heat": {
        "hazard": {
            "HIGH": {
                "action": "Activate municipal 'Extreme Heat Emergency Protocol': Deploy high-pressure cool misting fans and emergency water tankers.",
                "priority": RecommendationPriority.IMMEDIATE,
                "rationale": "Extreme ambient heat index exceeding 44C presents acute life-threatening risk of fatal heat stroke.",
                "suggested_next_step": "Position 2 municipal water misting stations at high-footfall open transit hubs.",
                "department": "Disaster Management Authority & Fire Services",
            },
            "MEDIUM": {
                "action": "Distribute chilled potable water and oral rehydration solution (ORS) packets at major bus terminals.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Thermal stress elevates rapid dehydration and heat exhaustion among commuters.",
                "suggested_next_step": "Coordinate with Red Cross volunteers to establish free hydration kiosks.",
                "department": "Public Health & Civil Defense",
            },
            "LOW": {
                "action": "Inspect public water drinking fountains and ensure continuous supply.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Preventative maintenance ensures baseline hydration access during seasonal warmth.",
                "suggested_next_step": "Service filter cartridges and test water pressure at civic dispensers.",
                "department": "Municipal Water Supply",
            },
        },
        "exposure": {
            "HIGH": {
                "action": "Enforce mandatory work stoppage for outdoor construction labor between 12:00 PM and 3:30 PM.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Direct solar irradiance during solar noon induces dangerous physiological thermal load.",
                "suggested_next_step": "Dispatch Labor Department inspectors to enforce heatwave labor safety protocols.",
                "department": "Department of Labor & Occupational Safety",
            },
            "MEDIUM": {
                "action": "Erect temporary thermal shade canopies with reflective tarpaulins over exposed transit queues.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Commuters exposed to unshaded metal roofs experience acute thermal discomfort.",
                "suggested_next_step": "Install 150 square meters of high-density UV-blocking green shade netting.",
                "department": "Public Transport Infrastructure",
            },
            "LOW": {
                "action": "Broadcast public thermal safety reminders across digital variable message road signs.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Encourage citizens to carry hydration bottles during afternoon hours.",
                "suggested_next_step": "Update smart city traffic displays with hydration advisory text.",
                "department": "Smart City Traffic Management",
            },
        },
        "vulnerability": {
            "HIGH": {
                "action": "Open air-conditioned civic community centers and libraries as designated public cooling sanctuaries.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Elderly and low-income residents in non-air-conditioned homes require immediate thermal refuge.",
                "suggested_next_step": "Extend civic center operating hours to 8:00 PM and provide seating and water.",
                "department": "Civic Social Welfare & Community Affairs",
            },
            "MEDIUM": {
                "action": "Perform welfare wellness checks on elderly and vulnerable citizens living in top-floor apartments.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Top floors absorb significant solar ceiling radiation, creating indoor heat traps.",
                "suggested_next_step": "Deploy community health workers to distribute ORS and thermal safety leaflets.",
                "department": "Community Health Outreach",
            },
            "LOW": {
                "action": "Promote high-albedo cool roof white paint coatings for residential tin/concrete roofs.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Passive cool roof coatings reflect 80% of solar radiation, reducing indoor temperatures by 3-5C.",
                "suggested_next_step": "Provide subsidized lime-wash coating kits to informal settlement households.",
                "department": "Urban Climate Resilience Cell",
            },
        },
        "duration": {
            "HIGH": {
                "action": "Sustained heatwave emergency broadcast: Mobilize paramedic heat-ambulance units with ice packs.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Consecutive days of high wet-bulb temperatures compound biological cardiovascular strain.",
                "suggested_next_step": "Equip 10 city emergency ambulances with dedicated rapid-cooling immersion ice packs.",
                "department": "Emergency Medical Services & Hospitals",
            },
            "MEDIUM": {
                "action": "Issue heat advisory bulletins through local radio, SMS, and civic mobile applications.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Multi-day elevated temperature forecast requires sustained citizen vigilance.",
                "suggested_next_step": "Transmit geo-targeted SMS alerts across municipal telecom cell towers.",
                "department": "Public Information Office",
            },
            "LOW": {
                "action": "Monitor regional meteorological weather radar and heat index forecasts.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Track incoming cloud cover and wind shifts.",
                "suggested_next_step": "Check daily meteorological bulletin.",
                "department": "Disaster Management Forecasting Cell",
            },
        },
    },
    "general_safety": {
        "hazard": {
            "HIGH": {
                "action": "Secure physical danger zone: Install reinforced steel manhole cover or erect structural scaffolding support.",
                "priority": RecommendationPriority.IMMEDIATE,
                "rationale": "Physical void or structural instability presents immediate life-safety fall or collapse danger.",
                "suggested_next_step": "Direct municipal emergency works crew to place heavy ductile iron cover or temporary steel plate.",
                "department": "Municipal Engineering Services",
            },
            "MEDIUM": {
                "action": "Cordon off hazardous void with caution tape and install temporary timber barrier.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Prevent accidental pedestrian trips or vehicle wheel drops into opening.",
                "suggested_next_step": "Anchor 4 wooden warning stakes and wrap high-visibility barricade tape.",
                "department": "Civic Safety Operations",
            },
            "LOW": {
                "action": "Repair broken civic park furniture or loose pavement paver.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Minor physical flaw poses no acute threat to public safety.",
                "suggested_next_step": "Log repair task for local ward handyman.",
                "department": "Ward Maintenance Cell",
            },
        },
        "exposure": {
            "HIGH": {
                "action": "Install temporary LED floodlights and audible cautionary beacons along unlit pedestrian route.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "High evening commuter volume traveling through dark hazardous zone elevates accident risk.",
                "suggested_next_step": "Deploy mobile solar-powered LED lighting trailer.",
                "department": "Civic Security & Street Lighting",
            },
            "MEDIUM": {
                "action": "Deploy high-visibility warning signs 30 meters ahead of obstruction.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Alert approaching pedestrians and cyclists to navigate around obstacle.",
                "suggested_next_step": "Place bright reflective 'Caution Watch Your Step' sign board.",
                "department": "Civic Safety Division",
            },
            "LOW": {
                "action": "Audit nighttime pedestrian footfall across sector.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Low pedestrian activity requires standard periodic monitoring.",
                "suggested_next_step": "Review lighting coverage during routine security rounds.",
                "department": "City Surveillance Operations",
            },
        },
        "vulnerability": {
            "HIGH": {
                "action": "Emergency structural reinforcement: Shoring and bracing of leaning boundary wall or cracked retaining slab.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Structural fatigue near public sidewalk threatens sudden collapse onto pedestrians.",
                "suggested_next_step": "Erect heavy timber raking shores to stabilize wall until permanent masonry reconstruction.",
                "department": "Structural Engineering & Building Inspection",
            },
            "MEDIUM": {
                "action": "Install handrail and anti-skid surface along degraded concrete ramp.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Assists elderly residents and persons with disabilities navigating uneven terrain.",
                "suggested_next_step": "Weld 2-inch galvanized steel handrail along outer ramp edge.",
                "department": "Civic Accessibility Infrastructure",
            },
            "LOW": {
                "action": "Inspect tactile paving pavers along pedestrian footpath.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Ensure guidance cues for visually impaired pedestrians remain intact.",
                "suggested_next_step": "Replace cracked tactile tile in routine maintenance.",
                "department": "Public Works Infrastructure",
            },
        },
        "duration": {
            "HIGH": {
                "action": "Immediate inter-agency intervention: Escalate long-standing civic defect directly to Municipal Commissioner.",
                "priority": RecommendationPriority.HIGH,
                "rationale": "Chronic unresolved status compounds civic vulnerability and legal liability.",
                "suggested_next_step": "Direct multi-departmental task force to execute permanent on-site resolution within 48 hours.",
                "department": "Municipal Commissioner Task Force",
            },
            "MEDIUM": {
                "action": "Re-assign open civic grievance to dedicated rapid-repair contractor.",
                "priority": RecommendationPriority.MEDIUM,
                "rationale": "Standard department backlog has delayed essential safety repair.",
                "suggested_next_step": "Issue expedited emergency work order.",
                "department": "Civic Grievance Resolution Cell",
            },
            "LOW": {
                "action": "Track resolution progress against standard civic service charter SLA.",
                "priority": RecommendationPriority.MONITOR,
                "rationale": "Timelines remain within acceptable operating thresholds.",
                "suggested_next_step": "Check status at next weekly departmental review.",
                "department": "Public Administration Bureau",
            },
        },
    },
}


def generate_recommendations(
    risk_score: float,
    risk_level: RiskLevel,
    category: str,
    primary_driver: str,
    secondary_driver: Optional[str] = None,
    incident_id: Optional[str] = None,
) -> RecommendationListResponse:
    """
    Generate context-aware civic recommendations deterministically based on:
    - Authoritative risk score and level (LOW, MEDIUM, HIGH)
    - Normalized incident category
    - Primary and secondary mathematical formula drivers (H, E, V, D)

    GUARANTEES:
    - Every recommendation item strictly possesses status: 'PROPOSED'.
    - Output is deterministic and testable.
    - Specific safety directives enforced for electrical hazards.
    """
    cat_key = normalize_category(category)
    cat_matrix = RECOMMENDATION_MATRIX.get(cat_key, RECOMMENDATION_MATRIX["general_safety"])

    level_key = risk_level.value  # "LOW", "MEDIUM", "HIGH"
    prim_driver_key = primary_driver.lower() if primary_driver in ["hazard", "exposure", "vulnerability", "duration"] else "hazard"

    recommendations: List[RecommendationItem] = []
    rec_counter = 1

    # 1. Primary Driver Targeted Action
    prim_driver_matrix = cat_matrix.get(prim_driver_key, cat_matrix["hazard"])
    prim_action_data = prim_driver_matrix.get(level_key, prim_driver_matrix["MEDIUM"])

    rec_id_1 = generate_recommendation_id(incident_id, rec_counter, prim_action_data["action"])
    recommendations.append(
        RecommendationItem(
            id=rec_id_1,
            action=prim_action_data["action"],
            priority=prim_action_data["priority"],
            rationale=f"Primary Driver: {prim_action_data['rationale']} (Risk Score: {risk_score:.1f}/100, Band: {risk_level.value})",
            suggested_next_step=prim_action_data["suggested_next_step"],
            status="PROPOSED",
            responsible_department=prim_action_data.get("department"),
        )
    )
    rec_counter += 1

    # 2. Secondary Driver Targeted Action (if distinct and available)
    if secondary_driver and secondary_driver.lower() != prim_driver_key:
        sec_driver_key = secondary_driver.lower()
        if sec_driver_key in cat_matrix:
            sec_driver_matrix = cat_matrix[sec_driver_key]
            # Calibrate priority for secondary driver
            sec_level_key = "MEDIUM" if level_key == "HIGH" else ("LOW" if level_key == "LOW" else "MEDIUM")
            sec_action_data = sec_driver_matrix.get(sec_level_key, sec_driver_matrix["LOW"])

            rec_id_2 = generate_recommendation_id(incident_id, rec_counter, sec_action_data["action"])
            recommendations.append(
                RecommendationItem(
                    id=rec_id_2,
                    action=sec_action_data["action"],
                    priority=sec_action_data["priority"],
                    rationale=f"Secondary Driver: {sec_action_data['rationale']}",
                    suggested_next_step=sec_action_data["suggested_next_step"],
                    status="PROPOSED",
                    responsible_department=sec_action_data.get("department"),
                )
            )
            rec_counter += 1

    # 3. Special Mandatory Safety Protocol for Electrical Hazards
    if cat_key == "electrical" and risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]:
        elec_protocol_action = (
            "Enforce immediate exclusion perimeter. Direct authorized power distribution utility "
            "personnel with certified dielectric protective equipment to isolate and verify zero electrical potential "
            "before any site access, cleanup, or water pumping. Do not treat any fixed distance as universally safe."
        )
        rec_id_elec = generate_recommendation_id(incident_id, rec_counter, elec_protocol_action)
        recommendations.append(
            RecommendationItem(
                id=rec_id_elec,
                action=elec_protocol_action,
                priority=RecommendationPriority.IMMEDIATE,
                rationale="Mandatory High-Voltage Safety Protocol: Direct contact or step-potential gradients in wet conditions risk fatal shock. Await authorized utility line isolation.",
                suggested_next_step="Confirm electric feeder de-energization with regional substation despatch engineer.",
                status="PROPOSED",
                responsible_department="State Power Distribution Corporation (DISCOM)",
            )
        )
        rec_counter += 1

    # 4. Routine Follow-Up / Monitoring Action
    monitor_action_data = cat_matrix.get("duration", cat_matrix["hazard"]).get("LOW")
    if monitor_action_data and len(recommendations) < 4:
        rec_id_mon = generate_recommendation_id(incident_id, rec_counter, monitor_action_data["action"])
        recommendations.append(
            RecommendationItem(
                id=rec_id_mon,
                action=monitor_action_data["action"],
                priority=RecommendationPriority.MONITOR,
                rationale="Operational Governance: Continuous observation ensures mitigation effectiveness.",
                suggested_next_step=monitor_action_data["suggested_next_step"],
                status="PROPOSED",
                responsible_department=monitor_action_data.get("department"),
            )
        )

    now_iso = datetime.now(timezone.utc).isoformat()

    return RecommendationListResponse(
        incident_id=incident_id,
        risk_score=risk_score,
        risk_level=risk_level,
        category=cat_key,
        dominant_factor=primary_driver,
        recommendations=recommendations,
        generated_at=now_iso,
    )


def verify_incident_recommendation_access(
    incident_data: Dict[str, Any],
    current_user: UserPrincipal,
) -> bool:
    """
    Enforce ownership and role-based authorization for incident recommendations:
    - ADMIN and ANALYST have full access across all incidents.
    - COMMUNITY_USER can only access recommendations for incidents they reported.
    Raises HTTPException(403) if unauthorized.
    """
    if current_user.role in [UserRole.ADMIN, UserRole.ANALYST]:
        return True

    reporter_uid = incident_data.get("reported_by") or incident_data.get("reporter_uid")
    if reporter_uid == current_user.uid:
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Community users are only authorized to view recommendations for incidents they reported.",
    )
