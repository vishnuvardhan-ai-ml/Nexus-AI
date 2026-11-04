"""
NEXUS AI API v1 Root Router.
Consolidates all v1 API modules and endpoint declarations.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, incidents, ai, geo

api_router = APIRouter()

# Core telemetry & diagnostics
api_router.include_router(health.router, tags=["System Telemetry"])

# Authentication & RBAC identity
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Roles"])

# Community Incident Management
api_router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])

# Risk Intelligence, Explainability & Scenario Simulation
api_router.include_router(ai.router, prefix="/ai", tags=["Risk Intelligence & AI Engine"])

# Geospatial Intelligence & Interactive Risk Mapping
api_router.include_router(geo.router, prefix="/geo", tags=["Geospatial Intelligence"])
