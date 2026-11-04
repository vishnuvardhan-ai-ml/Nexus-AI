# NEXUS AI — System Architecture & Design Specification

> **Platform**: Community Intelligence & Risk Decision Platform  
> **Status**: Milestone 1 & Milestone 2 (Auth & Incident Management) Completed  
> **Repository Mode**: Monorepo (`frontend/`, `backend/`, `docs/`)

---

## 1. Executive Overview

**NEXUS AI** is a civic-intelligence platform designed to aggregate community incident reports, classify them using lightweight machine learning, compute deterministic risk scores using an explainable multi-factor formula, run what-if intervention simulations, and dispatch actionable municipal recommendations.

### Core Pipeline:
```
REPORT ➔ ANALYZE ➔ PREDICT ➔ EXPLAIN ➔ SIMULATE ➔ RECOMMEND
```

---

## 2. Monorepo Structure

```
NEXUS-AI/
├── firestore.rules              # Production-grade Firestore CEL security rules
├── frontend/                    # React + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── context/             # AuthContext (Firebase Auth + RBAC)
│   │   ├── components/
│   │   │   ├── auth/            # ProtectedRoute
│   │   │   ├── layout/          # Navbar, Sidebar, DashboardLayout
│   │   │   └── ui/              # Button, Badge, StatCard, HealthStatusWidget
│   │   ├── pages/               # LandingPage, LoginPage, RegisterPage,
│   │   │                        # IncidentReportPage, IncidentListPage, IncidentDetailPage,
│   │   │                        # DashboardOverview, PlaceholderPage
│   │   ├── services/            # API client & Firebase Auth/Firestore client
│   │   ├── types/               # TypeScript data models and taxonomies
│   │   ├── App.tsx              # React Router route registry
│   │   ├── main.tsx             # Application bootstrap
│   │   └── index.css            # Cybernetic design tokens & glassmorphism
│   ├── package.json
│   ├── tailwind.config.js       # Deep navy (#070b14) & Cyan (#00f0ff) theme
│   ├── vite.config.ts
│   └── .env.example
├── backend/                     # Python + FastAPI + Pydantic + Firebase Admin
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py          # Firebase token verification & require_role RBAC
│   │   │   └── v1/
│   │   │       ├── endpoints/   # health.py, auth.py, incidents.py
│   │   │       └── router.py    # Consolidated v1 router
│   │   ├── core/
│   │   │   └── config.py        # Pydantic BaseSettings & Firebase config
│   │   ├── schemas/             # Pydantic models (health, incidents, user, risk)
│   │   ├── services/            # Firebase service, Incident service, ML classifier
│   │   └── main.py              # FastAPI app instance & middleware
│   ├── tests/                   # Pytest test suite
│   │   ├── conftest.py
│   │   ├── test_health.py
│   │   └── test_auth_and_incidents.py
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   └── architecture.md          # System architecture specification
├── .gitignore
└── README.md                    # Project overview & running instructions
```

---

## 3. Firestore Database Architecture

### Collection: `users/{userId}`
- **Document ID**: `{userId}` (matches Firebase Auth UID).
- **Schema**:
  - `uid`: `string` (matches document ID and `request.auth.uid`, immutable)
  - `email`: `string` (valid RFC 5322 format)
  - `displayName`: `string` (1–100 chars)
  - `role`: `string` enum (`COMMUNITY_USER`, `ANALYST`, `ADMIN`)
  - `createdAt`: `timestamp` (server timestamp, immutable)
  - `updatedAt`: `timestamp` (server timestamp)
- **Security Invariants**:
  - Unauthenticated reads and writes are rejected.
  - Users can read only their own user document (`isOwner(userId)`), while ADMINs can view all.
  - Standard user self-registration is strictly restricted to `role == 'COMMUNITY_USER'`. Self-escalation to `ANALYST` or `ADMIN` is rejected by CEL security rules.
  - Role modifications on `update` require verified `ADMIN` claims.

### Collection: `incidents/{incidentId}`
- **Document ID**: `{incidentId}` (server-generated unique ID, e.g. `inc_<12-hex>`).
- **Schema**:
  - `id`: `string` (matches document ID, immutable)
  - `title`: `string` (3–200 chars)
  - `description`: `string` (10–5000 chars)
  - `category`: `string` enum (`waterlogging`, `road_damage`, `electrical_hazard`, `waste_management`, `extreme_heat`)
  - `severity`: `string` enum (`LOW`, `MEDIUM`, `HIGH`)
  - `location`: `string` (2–250 chars)
  - `latitude`: `number | null` (-90.0 to +90.0)
  - `longitude`: `number | null` (-180.0 to +180.0)
  - `imageUrl`: `string | null` (HTTP/HTTPS URL or data URI)
  - `status`: `string` enum (`reported`, `investigating`, `mitigating`, `resolved`)
  - `reportedBy`: `string` (matches `request.auth.uid`, immutable)
  - `reporterEmail`: `string` (reporter email, immutable)
  - `createdAt`: `timestamp` (server timestamp, immutable)
  - `updatedAt`: `timestamp` (server timestamp)
- **Security Invariants**:
  - `read`: Open to the public and authenticated community for public civic awareness and risk heatmaps.
  - `create`: Authenticated users only; must bind `reportedBy == request.auth.uid`; initial status must be `'reported'`.
  - `update`: Original reporters can update descriptions while status is `'reported'`. Only `ANALYST` or `ADMIN` can transition statuses (`'investigating'`, `'mitigating'`, `'resolved'`).
  - `delete`: Only `ADMIN` or original reporter (while still `'reported'`).

---

## 4. Role-Based Access Control (RBAC)

1. **`COMMUNITY_USER`**:
   - Register account via email/password.
   - Submit new incident reports with geolocation and photo attachments.
   - View public incident stream and detail records.
   - Filter stream to "My Reports Only".
2. **`ANALYST`**:
   - All community capabilities.
   - Execute what-if scenario simulations.
   - Review transparent factor contributions and model diagnostics.
   - Transition incident investigation statuses.
3. **`ADMIN`**:
   - All analyst and community capabilities.
   - Configure model weights and system thresholds.
   - Dispatch emergency municipal work orders.
   - Assign user roles and manage system configuration.

---

## 5. Versioned REST API Contract

All backend routes are prefixed under `/api/v1`:

### System & Diagnostics
- `GET /api/v1/health` — Subsystem readiness and telemetry status.
- `GET /api/v1/docs` — Swagger OpenAPI interactive documentation.

### Authentication & Roles
- `GET /api/v1/auth/me` — Inspect caller's verified identity and RBAC role.
- `POST /api/v1/auth/sync-profile` — Synchronize profile document upon registration; strictly guarantees `COMMUNITY_USER`.

### Community Incidents
- `POST /api/v1/incidents` — Submit incident report (requires Bearer token).
- `GET /api/v1/incidents` — Query community incidents with taxonomy and status filters.
- `GET /api/v1/incidents/{incident_id}` — Retrieve full incident details by server-generated ID.
