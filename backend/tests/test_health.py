"""
Unit and integration tests for system health and telemetry endpoints.
"""
from datetime import datetime
from app.core.config import settings
from app.api.v1.endpoints.health import get_system_health
from app.main import root, app


def test_system_settings():
    """Verify application configuration defaults and API prefix."""
    assert settings.API_V1_STR == "/api/v1"
    assert "NEXUS AI" in settings.PROJECT_NAME
    assert settings.VERSION == "1.0.0"
    assert "http://localhost:5173" in settings.BACKEND_CORS_ORIGINS


def test_health_endpoint_logic():
    """Verify health endpoint returns valid schema, timestamps, and ready subsystems."""
    response = get_system_health()
    assert response.status == "healthy"
    assert response.service == settings.PROJECT_NAME
    assert response.version == settings.VERSION
    assert response.environment == settings.ENVIRONMENT
    assert response.subsystems.classifier == "ready"
    assert response.subsystems.risk_engine == "ready"
    assert response.subsystems.database == "standby"

    # Verify timestamp format
    parsed_time = datetime.fromisoformat(response.timestamp)
    assert parsed_time is not None


def test_root_endpoint_logic():
    """Verify root documentation and index response links."""
    import asyncio
    res = asyncio.run(root()) if asyncio.iscoroutinefunction(root) else root()
    # Handle if root is async or sync
    if hasattr(res, "__await__"):
        res = asyncio.run(res)
    assert "service" in res
    assert res["docs"] == "/api/v1/docs"
    assert res["health"] == "/api/v1/health"
