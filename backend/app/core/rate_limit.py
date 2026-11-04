"""
Production Rate Limiting for NEXUS AI.

Implements centralized, configurable rate limiting via Slowapi / Limits.
Supports in-memory storage (single-container / local development) and
Redis storage (distributed production clusters e.g. Cloud Run, Kubernetes, Render).
Enforces secure reverse-proxy IP extraction without trusting spoofed headers.
"""
import hashlib
import logging
from typing import Optional
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from functools import wraps
import inspect
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from app.core.config import settings

logger = logging.getLogger("nexus.security.ratelimit")


def get_client_rate_limit_key(request: Request) -> str:
    """
    Extract rate-limiting key for the client.
    
    1. If request contains an Authorization Bearer header:
       Uses authenticated user identity/token hash to partition limits per user,
       preventing entire corporate networks or shared NAT IPs from throttling each other.
    2. If request is unauthenticated:
       Extracts client IP. If the direct connection originates from a configured
       trusted reverse proxy (settings.TRUSTED_PROXIES), inspects X-Forwarded-For.
       Otherwise, ignores X-Forwarded-For to prevent client IP spoofing attacks.
    """
    # 1. Authenticated user key
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.strip().startswith("Bearer "):
        token = auth_header.strip()[7:].strip()
        if token:
            if token.startswith("dev-token:"):
                parts = token.split(":")
                if len(parts) >= 2:
                    return f"user:{parts[1]}"
            token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
            return f"user:{token_digest}"

    # 2. Unauthenticated client IP extraction
    direct_ip = request.client.host if request.client else "127.0.0.1"
    
    # Only trust X-Forwarded-For if incoming connection is from a trusted proxy
    trusted_proxies = set(settings.TRUSTED_PROXIES or ["127.0.0.1", "::1"])
    if direct_ip in trusted_proxies:
        xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
        if xff:
            forwarded_ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
            if forwarded_ips:
                return f"ip:{forwarded_ips[0]}"

    return f"ip:{direct_ip}"


# Centralized Limiter configuration
storage_backend = settings.REDIS_URL if settings.REDIS_URL else "memory://"

limiter = Limiter(
    key_func=get_client_rate_limit_key,
    default_limits=[settings.RATE_LIMIT_DEFAULT] if settings.RATE_LIMIT_ENABLED else [],
    storage_uri=storage_backend,
    enabled=settings.RATE_LIMIT_ENABLED,
)


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Consistent JSON error response for rate-limited requests complying with NEXUS AI standards.
    """
    response = JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Too many requests. Please retry in a few moments."},
    )
    try:
        if hasattr(request, "app") and hasattr(request.app.state, "limiter"):
            response = request.app.state.limiter._inject_headers(
                response, getattr(request.state, "view_rate_limit", None)
            )
    except Exception as e:
        logger.debug("Could not inject rate limit headers: %s", e)
        
    return response


def rate_limit(limit_value: str, **limit_kwargs):
    """
    Production rate-limiting decorator wrapping Slowapi.
    
    - In HTTP request context (FastAPI ASGI dispatch):
      Evaluates Slowapi rate limits and raises RateLimitExceeded (HTTP 429) if exceeded.
    - In direct Python function invocation context (unit tests / internal callers):
      Bypasses rate limiting cleanly if no Starlette Request is supplied, allowing
      existing test suites to directly invoke route handler functions without friction.
    """
    def decorator(func):
        slowapi_decorator = limiter.limit(limit_value, **limit_kwargs)
        decorated_func = slowapi_decorator(func)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            has_request = any(isinstance(a, Request) for a in args) or isinstance(kwargs.get("request"), Request)
            if not has_request:
                return func(*args, **kwargs)
            return decorated_func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            has_request = any(isinstance(a, Request) for a in args) or isinstance(kwargs.get("request"), Request)
            if not has_request:
                return await func(*args, **kwargs)
            return await decorated_func(*args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
