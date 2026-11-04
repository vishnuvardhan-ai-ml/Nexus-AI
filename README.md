# NEXUS AI — Community Intelligence & Risk Decision Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Vite](https://img.shields.io/badge/Frontend-Vite%205+-646CFF.svg?style=flat&logo=vite)](https://vitejs.dev)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6.svg?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4+-38B2AC.svg?style=flat&logo=tailwind-css)](https://tailwindcss.com)
[![Pytest](https://img.shields.io/badge/Tests-Pytest%20Passing-brightgreen.svg?style=flat&logo=pytest)](https://docs.pytest.org)

NEXUS AI is a full-stack civic intelligence and risk decision platform. It converts community incident reports into structured classifications, explainable multi-factor risk assessments, what-if scenario simulations, and actionable municipal recommendations.

---

## 🚀 Core Decision Workflow

```
REPORT ➔ ANALYZE ➔ PREDICT ➔ EXPLAIN ➔ SIMULATE ➔ RECOMMEND
```

1. **REPORT**: Community members submit geo-tagged incident reports across 5 core categories.
2. **ANALYZE**: Lightweight TF-IDF + Logistic Regression identifies category and extracts hazard entities.
3. **PREDICT**: Deterministic Risk Engine calculates scores using normalized factors:
   $$\text{Risk} = 0.4H + 0.3E + 0.2V + 0.1D$$
4. **EXPLAIN**: Multi-factor percentage breakdown removes black-box obscurity for municipal leaders.
5. **SIMULATE**: What-if scenario modeler forecasts the risk reduction of resource dispatches (pumps, barricades, routing).
6. **RECOMMEND**: Action center generates prioritized work-orders and emergency civic advisories.

---

## 🏛️ Monorepo Architecture

```
NEXUS-AI/
├── frontend/             # React 18, TypeScript, Vite, Tailwind CSS, Lucide icons
│   ├── src/
│   │   ├── components/   # UI elements (StatCard, Badge, Button, HealthStatusWidget) & Layout
│   │   ├── pages/        # LandingPage, DashboardOverview, PlaceholderPage
│   │   ├── services/     # API client service connecting to FastAPI health telemetry
│   │   ├── types/        # TypeScript interfaces for incidents, risk, and telemetry
│   │   ├── App.tsx       # Route definitions for all 10 platform modules
│   │   └── main.tsx      # React DOM bootstrap
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── .env.example
├── backend/              # Python 3.13, FastAPI, Pydantic, Scikit-learn
│   ├── app/
│   │   ├── api/v1/       # Versioned API routes (health, telemetry)
│   │   ├── core/         # Settings, environment configuration, CORS
│   │   ├── schemas/      # Pydantic schemas for health & telemetry
│   │   └── main.py       # FastAPI application entry point
│   ├── tests/            # Automated test suite (test_health.py)
│   ├── requirements.txt
│   └── .env.example
├── docs/                 # Architectural specifications
│   └── architecture.md
├── .gitignore
└── README.md
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- **Node.js** v18+ (tested on v24.13) & **npm** v10+
- **Python** 3.10+ (tested on v3.13.2)

---

### 2. Backend Setup (FastAPI)

1. Open a terminal in the `backend/` directory:
   ```bash
   cd backend
   ```

2. (Optional but recommended) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create environment configuration:
   ```bash
   copy .env.example .env     # Windows
   # or
   cp .env.example .env        # macOS/Linux
   ```

5. Run the test suite:
   ```bash
   python -m pytest -v
   ```

6. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - API Root: [http://localhost:8000](http://localhost:8000)
   - Interactive Swagger Docs: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
   - Health Telemetry: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### 3. Frontend Setup (React + Vite)

1. Open a separate terminal in the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create environment configuration:
   ```bash
   copy .env.example .env     # Windows
   # or
   cp .env.example .env        # macOS/Linux
   ```

4. Build and type-check:
   ```bash
   npm run build
   ```

5. Launch the Vite development server:
   ```bash
   npm run dev
   ```
   - Web Platform: [http://localhost:5173](http://localhost:5173)
   - Overview Console: [http://localhost:5173/dashboard](http://localhost:5173/dashboard)

---

## 🎨 Design System

- **Background**: Deep Navy (`#070b14` / `#0b1120`)
- **Accents**: Cyber Cyan (`#00f0ff` / `#06b6d4`) & Electric Blue (`#3b82f6`)
- **Risk Severity Colors**:
  - `0 – 29` **LOW**: Emerald (`#10b981`)
  - `30 – 59` **MEDIUM**: Amber (`#f59e0b`)
  - `60 – 100` **HIGH**: Rose (`#f43f5e`)
- **Typography**: `Inter` (UI prose) & `JetBrains Mono` (telemetry, scores, coordinates)
- **Glassmorphism**: Backdrop blur with subtle cyan glowing borders

---

## 📋 Milestone 1 Completion Status

- [x] Initialized monorepo structure (`frontend/`, `backend/`, `docs/`).
- [x] React + TypeScript + Vite frontend configured.
- [x] FastAPI + Pydantic backend configured.
- [x] Tailwind CSS configured with deep navy and cyan theme.
- [x] NEXUS AI design tokens and UI components built.
- [x] Backend `/api/v1/health` endpoint implemented with subsystem telemetry.
- [x] Modern Landing Page and Dashboard Shell built.
- [x] Frontend connected to backend health endpoint with real-time ping and latency indicator.
- [x] Architecture document (`docs/architecture.md`) and comprehensive README created.
- [x] Automated test suite passing with 100% success rate.
- [x] Production build verified with zero TypeScript or bundling errors.
