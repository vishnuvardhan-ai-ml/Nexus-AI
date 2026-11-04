"""
Pydantic schemas for health and system status.
"""
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field


class HealthSubsystems(BaseModel):
    classifier: str = Field(default="ready", description="TF-IDF & Logistic Classifier status")
    risk_engine: str = Field(default="ready", description="Transparent Risk Equation Engine status")
    database: str = Field(default="standby", description="Cloud Firestore connection status")


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Overall health state")
    service: str = Field(..., description="Service identifier name")
    version: str = Field(..., description="Service semantic version")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    environment: str = Field(..., description="Active runtime environment")
    subsystems: HealthSubsystems = Field(default_factory=HealthSubsystems, description="Subsystem operational states")
