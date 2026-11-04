"""
Production Security Headers Middleware for NEXUS AI.

Injects HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
and Permissions-Policy to enforce strict defense-in-depth across all HTTP responses.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.config import settings


# Content-Security-Policy crafted to permit React SPA, CartoDB Dark Matter tiles,
# Recharts SVG elements, Google Fonts, and Firebase Authentication endpoints without compromise.
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://apis.google.com https://*.firebaseapp.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "img-src 'self' data: blob: https://*.cartocdn.com https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org https://*.firebasestorage.app https://firebasestorage.googleapis.com; "
    "connect-src 'self' https://*.googleapis.com https://*.firebaseio.com https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://*.basemaps.cartocdn.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "frame-src 'self' https://*.firebaseapp.com https://*.firebase.com; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "base-uri 'self';"
)


def attach_security_headers(response: Response, is_https: bool = False) -> Response:
    """
    Attach standard defense-in-depth security headers to any Starlette / FastAPI response.
    """
    # 1. Prevent MIME-sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # 2. Defend against Clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # 3. Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # 4. Permissions Policy (Disables unused sensitive device APIs)
    response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=(), payment=()"

    # 5. Content Security Policy
    response.headers["Content-Security-Policy"] = CSP_POLICY

    # 6. HTTP Strict Transport Security (HSTS) - Enforce on HTTPS or in production
    if is_https or settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware attaching production security headers to all outbound responses.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        is_https = request.url.scheme == "https"
        return attach_security_headers(response, is_https=is_https)
