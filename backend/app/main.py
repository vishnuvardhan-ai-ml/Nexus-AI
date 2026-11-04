"""
NEXUS AI - Community Intelligence & Risk Decision Platform
FastAPI Application Entry Point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.rate_limit import limiter, custom_rate_limit_exceeded_handler
from app.api.v1.router import api_router
from app.services.firebase_service import initialize_firebase, shutdown_firebase


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    # 1. Fail-closed security validation: Abort startup if unsafe debug/wildcards exist in production
    settings.validate_production_security()

    # 2. Startup: Initialize Firebase Admin SDK connection
    initialize_firebase()
    yield
    # 3. Shutdown: Clean up Firebase Admin and Firestore connections
    shutdown_firebase()


# Conditionally expose interactive documentation: strictly disabled in production
is_prod = settings.ENVIRONMENT == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade backend for NEXUS AI: Community Intelligence & Risk Decision Platform. "
        "Provides incident classification, transparent risk calculation, what-if simulation, and action dispatch."
    ),
    openapi_url=None if is_prod else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if is_prod else f"{settings.API_V1_STR}/docs",
    redoc_url=None if is_prod else f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Register Slowapi centralized rate limiter and custom 429 exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

# 1. Attach Production Security Headers Middleware (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Configure Hardened Cross-Origin Resource Sharing (CORS)
# Restricts origins to explicit trusted list, restricts permitted methods & headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
)

# Register versioned API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def root():
    """Root platform index returning service status and documentation link."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": None if is_prod else f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
