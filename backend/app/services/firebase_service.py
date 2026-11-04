"""
Firebase Admin SDK and Cloud Firestore service initialization for NEXUS AI.
Target Project: nexus-ai-4a631
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, auth, firestore
from fastapi import HTTPException, status
from app.core.config import settings
from app.schemas.user import UserRole, UserPrincipal

logger = logging.getLogger("nexus.firebase")

_firebase_app: Optional[firebase_admin.App] = None
_firestore_db = None

# Base directory for resolving backend paths relative to backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def resolve_service_account_path() -> Optional[Path]:
    """
    Resolve the service-account credentials path strictly relative to the backend directory,
    never relying on the terminal working directory.
    """
    path_setting = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None) or getattr(settings, "FIREBASE_SERVICE_ACCOUNT_PATH", None) or "secrets/firebase-service-account.json"
    p = Path(path_setting)
    if p.is_absolute():
        return p.resolve()

    # If configured as 'backend/secrets/...', strip leading 'backend/' when resolving from BACKEND_DIR
    parts = list(p.parts)
    if parts and parts[0] == "backend":
        resolved = BACKEND_DIR.joinpath(*parts[1:])
    else:
        resolved = BACKEND_DIR / p

    return resolved.resolve()


def initialize_firebase() -> firebase_admin.App:
    """
    Initialize Firebase Admin SDK once during application startup.
    Supports multiple production credential sources:
      1. Google Application Default Credentials (ADC) for Google Cloud Run (settings.FIREBASE_USE_ADC)
      2. Environment variable JSON string (settings.FIREBASE_CREDENTIALS_JSON) for container hosts (Render, Railway)
      3. Local service-account key file (settings.FIREBASE_SERVICE_ACCOUNT_PATH / FIREBASE_CREDENTIALS_PATH)
    Validates credentials and verifies project ID is exactly 'nexus-ai-4a631'.
    Fails clearly if credentials are missing, invalid, or belong to another project.
    Never logs credentials or secret keys.
    """
    global _firebase_app, _firestore_db

    # Check if app is already initialized in this process (e.g. reload or multiple imports)
    if len(firebase_admin._apps) > 0:
        _firebase_app = firebase_admin.get_app()
        if _firestore_db is None:
            try:
                _firestore_db = firestore.client(_firebase_app)
            except Exception as e:
                logger.warning("Could not obtain existing Firestore client: %s", e)
        return _firebase_app

    expected_project = settings.FIREBASE_PROJECT_ID
    cred = None

    # 1. Google Application Default Credentials (ADC for Cloud Run / GKE)
    if getattr(settings, "FIREBASE_USE_ADC", False):
        try:
            logger.info("Initializing Firebase Admin SDK using Google Application Default Credentials (ADC)...")
            cred = credentials.ApplicationDefault()
            # If ADC provides a project_id, verify it matches
            if getattr(cred, "project_id", None) and cred.project_id != expected_project:
                raise ValueError(
                    f"ADC project ID '{cred.project_id}' does not match expected project '{expected_project}'."
                )
        except Exception as exc:
            raise RuntimeError(f"Failed to obtain Application Default Credentials: {exc}") from exc

    # 2. FIREBASE_CREDENTIALS_JSON environment variable (e.g. Render, Railway, GitHub Actions)
    elif getattr(settings, "FIREBASE_CREDENTIALS_JSON", None):
        try:
            raw_json = settings.FIREBASE_CREDENTIALS_JSON.strip()
            # Handle potential base64 encoding if provided in base64
            if not raw_json.startswith("{"):
                import base64
                try:
                    raw_json = base64.b64decode(raw_json).decode("utf-8")
                except Exception:
                    pass
            cert_dict = json.loads(raw_json)
            if not isinstance(cert_dict, dict):
                raise ValueError("Parsed FIREBASE_CREDENTIALS_JSON is not a JSON object.")
            cred = credentials.Certificate(cert_dict)
            if cred.project_id != expected_project:
                raise ValueError(
                    f"Credentials JSON project ID '{cred.project_id}' does not match expected project '{expected_project}'."
                )
            logger.info("Loaded Firebase credentials from FIREBASE_CREDENTIALS_JSON environment variable.")
        except Exception as exc:
            raise ValueError(f"Invalid FIREBASE_CREDENTIALS_JSON configuration: {exc}") from exc

    # 3. Local Service-Account File Path
    else:
        cred_path = resolve_service_account_path()
        if not cred_path or not cred_path.exists() or not cred_path.is_file():
            raise FileNotFoundError(
                f"Firebase service account file not found at '{cred_path}'. "
                f"Please verify FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_CREDENTIALS_JSON."
            )

        try:
            cred = credentials.Certificate(str(cred_path))
        except Exception as exc:
            raise ValueError(
                f"Invalid Firebase service-account JSON at '{cred_path}': {exc}"
            ) from exc

        # Strictly verify the service-account belongs to expected project
        if cred.project_id != expected_project:
            raise ValueError(
                f"Service account project ID '{cred.project_id}' does not match expected project '{expected_project}'. "
                "Rejecting configuration to prevent cross-project contamination."
            )

    options = {
        "projectId": expected_project,
    }
    if settings.FIREBASE_STORAGE_BUCKET:
        options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET

    try:
        _firebase_app = firebase_admin.initialize_app(cred, options)
        _firestore_db = firestore.client(_firebase_app)
        logger.info(
            "Firebase Admin SDK successfully connected to project '%s' and Cloud Firestore.",
            expected_project,
        )
        return _firebase_app
    except Exception as exc:
        logger.error("Failed to initialize Firebase Admin SDK: %s", exc)
        raise RuntimeError(f"Firebase Admin initialization failed: {exc}") from exc


def shutdown_firebase() -> None:
    """Clean up Firebase Admin resources during application shutdown."""
    global _firebase_app, _firestore_db
    if _firebase_app is not None:
        try:
            logger.info("Cleaning up Firebase Admin resources...")
            firebase_admin.delete_app(_firebase_app)
        except Exception as exc:
            logger.warning("Error deleting Firebase app on shutdown: %s", exc)
        finally:
            _firebase_app = None
            _firestore_db = None


def is_firebase_configured() -> bool:
    """Return whether Firebase Admin SDK is connected with live credentials."""
    return _firebase_app is not None and _firestore_db is not None


def get_firestore_client():
    """Return initialized Cloud Firestore client or initialize if needed."""
    global _firestore_db
    if _firestore_db is None:
        initialize_firebase()
    if _firestore_db is None:
        raise RuntimeError("Cloud Firestore client is not initialized.")
    return _firestore_db


def set_firestore_client_for_testing(mock_client):
    """Testing hook to inject a mock or test Firestore client for unit tests."""
    global _firestore_db
    _firestore_db = mock_client


def verify_firebase_id_token(id_token: str) -> UserPrincipal:
    """
    Verify incoming Firebase Bearer ID token.
    Enforces role-based claims without trusting client payload.
    Rejects missing, invalid, or expired tokens with HTTP 401.
    """
    if not id_token or not id_token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Unit testing mock handler:
    # Explicitly labeled as test mock tokens and strictly prohibited in production mode.
    if id_token.startswith("dev-token:"):
        if settings.ENVIRONMENT == "production" or not settings.DEBUG or settings.ENVIRONMENT not in ("development", "test"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Development test tokens are strictly prohibited in production mode.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        parts = id_token.split(":")
        if len(parts) >= 4:
            uid, email, role_str = parts[1], parts[2], parts[3]
            role = UserRole.COMMUNITY_USER
            if role_str in [r.value for r in UserRole]:
                role = UserRole(role_str)
            return UserPrincipal(uid=uid, email=email, role=role, claims={"test_mock": True})

    # Live Firebase ID Token Verification
    try:
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unverified Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    uid = decoded_token.get("uid")
    email = decoded_token.get("email", "")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token contains no UID claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Determine verified role strictly from custom claim or Firestore users/{uid}
    verified_role = UserRole.COMMUNITY_USER
    raw_role = decoded_token.get("role")
    if raw_role in [r.value for r in UserRole]:
        verified_role = UserRole(raw_role)
    else:
        # Fallback: check Firestore users/{uid} for assigned trusted role
        try:
            db = get_firestore_client()
            user_ref = db.collection("users").document(uid)
            user_doc = user_ref.get()
            if user_doc.exists:
                data = user_doc.to_dict() or {}
                doc_role = data.get("role")
                if doc_role in [r.value for r in UserRole]:
                    verified_role = UserRole(doc_role)
            else:
                # Initialize new user profile document with strict COMMUNITY_USER default
                now_iso = datetime.now(timezone.utc).isoformat()
                user_ref.set({
                    "uid": uid,
                    "email": email,
                    "role": UserRole.COMMUNITY_USER.value,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                })
        except Exception as doc_err:
            logger.warning("Could not inspect/initialize Firestore user document: %s", doc_err)

    return UserPrincipal(
        uid=uid,
        email=email,
        role=verified_role,
        claims=decoded_token,
    )
