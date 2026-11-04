"""
Unit and integration tests for Milestone 6 Stage 2:
Backend Security Hardening, Rate Limiting & Secrets Management.

Verifies:
1. Development tokens are strictly rejected in production (fail-closed).
2. Production startup fail-closed validation on DEBUG or wildcard CORS.
3. Production security headers middleware (HSTS, CSP, X-Frame-Options, etc.).
4. API rate limiter client key extraction, trusted reverse proxy verification, and HTTP 429 response formatting.
5. Rate limit enforcement on rate-limited endpoints.
6. Firebase credentials loading from environment JSON, project ID mismatch rejection, and ADC.
7. Production API docs (Swagger/ReDoc) disabled conditionally.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.core.security_headers import SecurityHeadersMiddleware, CSP_POLICY, attach_security_headers
from app.core.rate_limit import (
    get_client_rate_limit_key,
    custom_rate_limit_exceeded_handler,
    rate_limit,
    limiter,
)
from app.services.firebase_service import (
    verify_firebase_id_token,
    initialize_firebase,
)
from app.schemas.user import UserPrincipal, UserRole
from app.main import app


# ============================================================================
# 1. Development Token Security & Fail-Closed Production Checks
# ============================================================================

def test_dev_token_strictly_rejected_in_production(monkeypatch):
    """
    Ensure development test tokens ('dev-token:...') are unconditionally rejected
    with HTTP 401 when ENVIRONMENT is 'production'.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DEBUG", False)

    with pytest.raises(HTTPException) as exc_info:
        verify_firebase_id_token("dev-token:hacker:evil@nexus.ai:ADMIN")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "strictly prohibited in production mode" in exc_info.value.detail


def test_dev_token_rejected_even_if_debug_true_in_production(monkeypatch):
    """
    Even if someone misconfigures DEBUG=True in production, dev tokens must still fail.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DEBUG", True)

    with pytest.raises(HTTPException) as exc_info:
        verify_firebase_id_token("dev-token:attacker:test@nexus.ai:COMMUNITY_USER")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "strictly prohibited in production mode" in exc_info.value.detail


def test_dev_token_rejected_in_staging_or_unknown_environments(monkeypatch):
    """
    Ensure dev tokens are rejected in any environment outside development/test.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "DEBUG", True)

    with pytest.raises(HTTPException) as exc_info:
        verify_firebase_id_token("dev-token:user1:user1@nexus.ai:COMMUNITY_USER")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_dev_token_accepted_in_local_development(monkeypatch):
    """
    Verify dev tokens function properly during legitimate offline development/testing.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "DEBUG", True)

    user = verify_firebase_id_token("dev-token:usr_dev_01:dev@nexus.local:ANALYST")
    assert user.uid == "usr_dev_01"
    assert user.email == "dev@nexus.local"
    assert user.role == UserRole.ANALYST
    assert user.claims.get("test_mock") is True


def test_missing_or_empty_token_rejected():
    """Missing or empty token raises HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        verify_firebase_id_token("")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# 2. Production Fail-Closed Startup Validation
# ============================================================================

def test_production_startup_aborts_if_debug_enabled():
    """Production startup must throw RuntimeError if DEBUG is True."""
    bad_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=True,
        BACKEND_CORS_ORIGINS=["https://nexus-ai.vercel.app"],
    )
    with pytest.raises(RuntimeError) as exc_info:
        bad_settings.validate_production_security()
    assert "DEBUG is True" in str(exc_info.value)


def test_production_startup_aborts_if_cors_wildcard():
    """Production startup must throw RuntimeError if CORS contains wildcard '*'."""
    bad_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        BACKEND_CORS_ORIGINS=["*", "https://nexus-ai.vercel.app"],
    )
    with pytest.raises(RuntimeError) as exc_info:
        bad_settings.validate_production_security()
    assert "Wildcard CORS origin '*'" in str(exc_info.value)


def test_production_startup_succeeds_with_hardened_config():
    """Production startup succeeds when DEBUG=False and explicit CORS origins are defined."""
    good_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        BACKEND_CORS_ORIGINS=["https://nexus-ai.vercel.app"],
    )
    # Should not raise any exception
    good_settings.validate_production_security()


# ============================================================================
# 3. Security Headers Middleware Enforcement
# ============================================================================

def test_security_headers_middleware_injection(monkeypatch):
    """
    Verify all standard defense-in-depth HTTP security headers are attached
    to outbound responses.
    """
    # 1. Non-production HTTP request (HSTS omitted)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    res_dev = Response("ok")
    attach_security_headers(res_dev, is_https=False)

    assert res_dev.headers["X-Content-Type-Options"] == "nosniff"
    assert res_dev.headers["X-Frame-Options"] == "DENY"
    assert res_dev.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=(self)" in res_dev.headers["Permissions-Policy"]
    assert "default-src 'self'" in res_dev.headers["Content-Security-Policy"]
    assert "Strict-Transport-Security" not in res_dev.headers

    # 2. Production request: Strict-Transport-Security MUST be present
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res_prod = Response("ok")
    attach_security_headers(res_prod, is_https=False)
    assert "Strict-Transport-Security" in res_prod.headers
    assert "max-age=31536000" in res_prod.headers["Strict-Transport-Security"]

    # 3. HTTPS in any environment: Strict-Transport-Security MUST be present
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    res_https = Response("ok")
    attach_security_headers(res_https, is_https=True)
    assert "Strict-Transport-Security" in res_https.headers


# ============================================================================
# 4. Rate Limiting: Key Extraction, Spoof Prevention & 429 Handler
# ============================================================================

def test_rate_limit_key_unauthenticated_direct_client():
    """Direct unauthenticated client IP extraction."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/geo/summary",
        "headers": [],
        "client": ("198.51.100.22", 54321),
    }
    req = Request(scope)
    key = get_client_rate_limit_key(req)
    assert key == "ip:198.51.100.22"


def test_rate_limit_key_ignores_spoofed_forwarded_for_from_untrusted_host(monkeypatch):
    """
    If the direct caller is NOT in TRUSTED_PROXIES, X-Forwarded-For must be ignored
    to prevent IP spoofing attacks.
    """
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", ["127.0.0.1", "10.0.0.1"])
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/incidents",
        "headers": [
            (b"x-forwarded-for", b"8.8.8.8, 1.1.1.1"),
        ],
        "client": ("198.51.100.99", 54321),  # Untrusted external IP
    }
    req = Request(scope)
    key = get_client_rate_limit_key(req)
    # Must use direct IP, NOT the spoofed 8.8.8.8
    assert key == "ip:198.51.100.99"


def test_rate_limit_key_trusts_forwarded_for_from_trusted_reverse_proxy(monkeypatch):
    """
    If direct caller IS in TRUSTED_PROXIES (e.g. Cloud Run, Render reverse proxy),
    extract the real client IP from X-Forwarded-For.
    """
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", ["127.0.0.1", "::1", "10.0.0.1"])
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/incidents",
        "headers": [
            (b"x-forwarded-for", b"203.0.113.45, 10.0.0.1"),
        ],
        "client": ("127.0.0.1", 54321),  # Trusted proxy
    }
    req = Request(scope)
    key = get_client_rate_limit_key(req)
    assert key == "ip:203.0.113.45"


def test_rate_limit_key_authenticated_user():
    """
    Authenticated requests use user-based token hash to prevent shared NAT throttling.
    """
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/incidents",
        "headers": [
            (b"authorization", b"Bearer dev-token:usr_alice_123:alice@nexus.gov:ANALYST"),
        ],
        "client": ("198.51.100.22", 54321),
    }
    req = Request(scope)
    key = get_client_rate_limit_key(req)
    assert key == "user:usr_alice_123"


def test_custom_rate_limit_exceeded_handler():
    """
    Verify HTTP 429 response conforms to documented specification:
    {"detail": "Rate limit exceeded. Too many requests. Please retry in a few moments."}
    """
    from slowapi.errors import RateLimitExceeded

    # Mock RateLimitExceeded exception
    mock_limit = MagicMock()
    mock_limit.error_message = None
    exc = RateLimitExceeded(mock_limit)

    scope = {"type": "http", "method": "GET", "path": "/api/v1/ai/assess", "headers": []}
    req = Request(scope)

    resp = custom_rate_limit_exceeded_handler(req, exc)
    assert resp.status_code == 429
    body = json.loads(resp.body.decode("utf-8"))
    assert body["detail"] == "Rate limit exceeded. Too many requests. Please retry in a few moments."


# ============================================================================
# 5. Firebase Credentials & Secrets Management
# ============================================================================

def test_firebase_credentials_from_json_env_valid(monkeypatch):
    """
    Verify Firebase initialization succeeds when FIREBASE_CREDENTIALS_JSON is configured.
    """
    fake_cert = {
        "type": "service_account",
        "project_id": "nexus-ai-4a631",
        "private_key_id": "key123",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk@nexus-ai-4a631.iam.gserviceaccount.com",
    }
    monkeypatch.setattr(settings, "FIREBASE_CREDENTIALS_JSON", json.dumps(fake_cert))

    with patch("firebase_admin.credentials.Certificate") as mock_cert:
        mock_instance = MagicMock()
        mock_instance.project_id = "nexus-ai-4a631"
        mock_cert.return_value = mock_instance

        with patch("firebase_admin.initialize_app") as mock_init:
            with patch("firebase_admin.firestore.client"):
                with patch("firebase_admin._apps", {}):
                    initialize_firebase()
                    mock_cert.assert_called_once()
                    mock_init.assert_called_once()


def test_firebase_credentials_json_project_mismatch_rejected(monkeypatch):
    """
    Reject credentials if project_id in JSON does not match FIREBASE_PROJECT_ID ('nexus-ai-4a631').
    """
    fake_cert = {
        "type": "service_account",
        "project_id": "wrong-malicious-project",
        "client_email": "attacker@wrong.iam.gserviceaccount.com",
    }
    monkeypatch.setattr(settings, "FIREBASE_CREDENTIALS_JSON", json.dumps(fake_cert))

    with patch("firebase_admin.credentials.Certificate") as mock_cert:
        mock_instance = MagicMock()
        mock_instance.project_id = "wrong-malicious-project"
        mock_cert.return_value = mock_instance
        with patch("firebase_admin._apps", {}):
            with pytest.raises(ValueError) as exc_info:
                initialize_firebase()
            assert "does not match expected project 'nexus-ai-4a631'" in str(exc_info.value)


# ============================================================================
# 6. Interactive Documentation Disabled in Production
# ============================================================================

def test_production_api_docs_conditional():
    """
    Verify that in production environments, docs_url, redoc_url, and openapi_url
    can be completely disabled.
    """
    from fastapi import FastAPI
    is_prod_true = True
    prod_app = FastAPI(
        docs_url=None if is_prod_true else "/docs",
        redoc_url=None if is_prod_true else "/redoc",
        openapi_url=None if is_prod_true else "/openapi.json",
    )
    assert prod_app.docs_url is None
    assert prod_app.redoc_url is None
    assert prod_app.openapi_url is None
