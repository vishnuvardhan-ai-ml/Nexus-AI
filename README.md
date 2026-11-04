# NEXUS AI — Community Intelligence & Municipal Risk Decision Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Vite](https://img.shields.io/badge/Frontend-Vite%205+-646CFF.svg?style=flat&logo=vite)](https://vitejs.dev)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6.svg?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4+-38B2AC.svg?style=flat&logo=tailwind-css)](https://tailwindcss.com)
[![Tests](https://img.shields.io/badge/Tests-124%20Passing%20(100%25)-brightgreen.svg?style=flat&logo=pytest)](https://docs.pytest.org)
[![Firebase](https://img.shields.io/badge/Database-Cloud%20Firestore-FFA000.svg?style=flat&logo=firebase)](https://firebase.google.com)
[![Security](https://img.shields.io/badge/Security-HSTS%20%7C%20CSP%20%7C%20Slowapi%20RateLimit-blueviolet.svg?style=flat)](https://owasp.org)

NEXUS AI is a full-stack, enterprise-grade civic hazard intelligence and municipal decision-support platform. It bridges community crowdsourced hazard reporting with deterministic mathematical risk calculation, geospatial clustering, interactive what-if scenario simulations, and automated municipal mitigation briefs.

---

## 🌐 Live Production Deployments

| Component | Target Platform | URL |
| :--- | :--- | :--- |
| **Frontend Application** | **Vercel** | `https://nexus-ai.vercel.app` |
| **Backend API Gateway** | **Google Cloud Run / Render** | `https://nexus-ai-backend.onrender.com` |
| **Platform Health Telemetry** | Production Endpoint | `GET /api/v1/health` |
| **Target Firebase Project** | Google Cloud / Firebase | `nexus-ai-4a631` |

---

## 🏛️ Platform Architecture & Features

```
[ Community / Field ] ──> [ React 18 + Vite SPA ] ──Bearer Token──> [ FastAPI 0.115 Backend ]
                                     │                                       │
                         [ CartoDB Dark Matter ]                   [ Rate Limiting & Auth ]
                                     │                                       │
                            [ Live Risk Map ]               ┌────────────────┴────────────────┐
                                                            ▼                                 ▼
                                                 [ Cloud Firestore DB ]          [ Deterministic Risk Engine ]
                                                   `nexus-ai-4a631`              R = 0.4H + 0.3E + 0.2V + 0.1D
                                                                                              │
                                                                                 [ What-If Mitigation Engine ]
                                                                                 [ Multi-Scenario Planner ]
```

### Key Modules:
1. **Community Incident Ingestion**: Geo-tagged reporting across 6 standardized civic hazard categories (*waterlogging, road_damage, electrical_hazard, waste_management, extreme_heat, general_safety*).
2. **Deterministic Risk Formula**: Transparent, explainable risk calculations based on:
   $$R = 0.4H + 0.3E + 0.2V + 0.1D$$
   Eliminates municipal black-box ambiguity with exact factor attribution and classification transitions (LOW, MEDIUM, HIGH, CRITICAL).
3. **Geospatial Intelligence Map**: High-performance interactive Leaflet & CartoDB Dark Matter visualization with RFC 7946 GeoJSON, bounding-box spatial filtering, exploratory grid clustering, and privacy coordinate generalization (~1km) for non-owner public views.
4. **Interactive What-If Simulation Engine**: Multi-scenario builder comparing 2 to 5 competing municipal interventions against a common baseline incident. Computes risk deltas, cost-effectiveness (points reduced per ₹1 Lakh), and multi-criteria prioritization.
5. **Executive Municipal Mitigation Briefs**: Automated generation of structured municipal decision briefs and downloadable Markdown reports with status `PROPOSED`.
6. **Hardened Production Security**:
   - Strictly fails closed if `DEBUG=True` in production.
   - Development mock tokens unconditionally rejected in production (`HTTP 401`).
   - Slowapi centralized rate limiting with reverse-proxy spoofing protection.
   - Strict Content Security Policy (CSP), HSTS, X-Frame-Options (`DENY`), and nosniff headers.
   - Google Application Default Credentials (ADC) support for keyless Cloud Run container deployments.

---

## 🔑 Role-Based Access Control (RBAC) & Test Accounts

NEXUS AI enforces strict separation of privileges between community reporters and municipal authorities:

| Role | Permissions |
| :--- | :--- |
| **`COMMUNITY_USER`** | Submit incidents, view public map (with generalized coordinates), inspect and simulate mitigation strictly for their own reported incidents. Restricted from viewing internal citywide records or running standalone simulations. |
| **`ANALYST`** | Full access to citywide incident registry, high-precision geospatial coordinates, authoritative risk assessments, multi-scenario simulations, and municipal executive brief generation. |
| **`ADMIN`** | Full administrative oversight, user role auditing, system health telemetry, and municipal policy configuration. |

---

## 🚀 Rapid Deployment Guide

### Option 1: Deploy Backend to Google Cloud Run (Recommended)

Google Cloud Run provides serverless container execution with keyless Application Default Credentials (ADC):

1. **Build & Deploy via Cloud Console**:
   - Go to [Google Cloud Run Console](https://console.cloud.google.com/run).
   - Click **Create Service** ➔ **Continuously deploy from a repository**.
   - Select your GitHub repository.
   - **Build context**: Set to repository root or `backend`.
   - **Build type**: Select `Dockerfile` (`backend/Dockerfile`).
   - **Service name**: `nexus-ai-backend`.
   - **Region**: Select your preferred region (e.g. `us-central1`).
   - **Authentication**: Allow unauthenticated invocations (public API).

2. **Configure Environment Variables**:
   Under **Container, Networking, Security**:
   ```ini
   ENVIRONMENT=production
   DEBUG=false
   FIREBASE_PROJECT_ID=nexus-ai-4a631
   FIREBASE_USE_ADC=true
   BACKEND_CORS_ORIGINS=["https://nexus-ai.vercel.app"]
   ```

3. **Grant Service Account Permissions**:
   Under Cloud Run **Security**, ensure the runtime Service Account has the **Cloud Datastore User** and **Firebase Admin SDK Administrator Service Agent** roles on project `nexus-ai-4a631`. This enables zero-key, fully secure Firestore access!

---

### Option 2: Deploy Backend to Render (Instant 1-Click Fallback)

If Google Cloud permissions or billing are not configured:

1. Log in to [Render.com](https://render.com).
2. Click **New +** ➔ **Blueprint** (or **Web Service**).
3. Connect your GitHub repository. Render will automatically detect [`render.yaml`](file:///c:/Users/USER/OneDrive/Desktop/Nexus AI/render.yaml).
4. Set Environment Variables in Render Dashboard:
   - `FIREBASE_CREDENTIALS_JSON`: Paste the raw contents of `secrets/firebase-service-account.json`.
   - `BACKEND_CORS_ORIGINS`: `["https://nexus-ai.vercel.app"]`.
5. Click **Deploy**. Your backend will be live at `https://nexus-ai-backend.onrender.com`.

---

### Option 3: Deploy Frontend to Vercel

1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** ➔ **Project** and import your GitHub repository.
3. **Configure Project Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `tsc && vite build`
   - **Output Directory**: `dist`
4. **Environment Variables**:
   ```ini
   VITE_API_BASE_URL=https://<your-backend-domain>/api/v1
   VITE_FIREBASE_API_KEY=AIzaSyAOvmfSpaEGeaI5iDSq4npV86pIdxc4juk
   VITE_FIREBASE_AUTH_DOMAIN=nexus-ai-4a631.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=nexus-ai-4a631
   VITE_FIREBASE_STORAGE_BUCKET=nexus-ai-4a631.firebasestorage.app
   VITE_FIREBASE_MESSAGING_SENDER_ID=114786658890
   VITE_FIREBASE_APP_ID=1:114786658890:web:93077aeea392000a27d4b3
   ```
5. Click **Deploy**. Vercel will build the frontend and serve it globally with [`frontend/vercel.json`](file:///c:/Users/USER/OneDrive/Desktop/Nexus AI/frontend/vercel.json) client-side routing support.

---

## 🧪 Automated Test Suite & Verification

The NEXUS AI test suite verifies risk formula precision, geospatial clustering, simulation invariance, rate limiting, and security rules:

```bash
# Run complete test suite (124 tests)
python -m pytest backend/tests/ -v
```

### Verification Result:
```
backend/tests/test_ai_endpoints.py .................................. [ 27%]
backend/tests/test_auth_and_incidents.py ............................ [ 50%]
backend/tests/test_geo_endpoints.py .........                         [ 57%]
backend/tests/test_health.py ...                                      [ 59%]
backend/tests/test_mitigation_endpoints.py ......................     [ 77%]
backend/tests/test_mitigation_service.py ............                 [ 87%]
backend/tests/test_ml_pipeline.py .                                   [ 87%]
backend/tests/test_recommendation_service.py .                        [ 88%]
backend/tests/test_risk_engine.py ......                              [ 93%]
backend/tests/test_security_hardening.py .................            [100%]

======================== 124 passed, 1 warning in 7.27s ========================
```

---

## 🔒 Security Commitments

- **No Secrets in Version Control**: Service account credentials and `.env` files are strictly excluded via `.gitignore` and `.dockerignore`.
- **Fail-Closed Principle**: The API strictly terminates startup if `DEBUG=True` is detected in a production environment.
- **Data Integrity**: What-If scenario simulations are guaranteed non-destructive and in-memory; they never alter or pollute production incident records.
- **OWASP Compliance**: Injected HSTS, Clickjacking protection (`X-Frame-Options: DENY`), MIME protection (`nosniff`), and strict Content Security Policy.

---

## 📄 License & Attribution

Developed for the NEXUS AI Municipal Intelligence Initiative. Built with FastAPI, React, Leaflet, and Cloud Firestore.
