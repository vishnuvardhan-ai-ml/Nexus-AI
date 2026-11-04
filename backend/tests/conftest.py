"""
Pytest configuration and shared test fixtures for NEXUS AI backend.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    """Synchronous test client for FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client
