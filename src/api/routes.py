"""API routes for detection ingestion with CoT/TAK output."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional, Set
from src.models.schemas import DetectionInput, ErrorResponse
from src.services.detection_service import DetectionService
from src.services.cot_service import CotService
from src.services.jwt_service import JWTService
from src.services.rate_limiter_service import RateLimiterService
from src.services.api_key_service import APIKeyService, APIKeyScope
from src.services.security_service import SecurityAuditLog, SecurityEventType
from src.database import get_db_session
from src.config import get_config
from src.api.auth import verify_jwt_token

router = APIRouter(prefix="/api/v1", tags=["detections"])

# Shared service instances (singleton per process)
_rate_limiter: Optional[RateLimiterService] = None
_api_key_service: Optional[APIKeyService] = None
_security_audit_log: Optional[SecurityAuditLog] = None


def get_rate_limiter() -> RateLimiterService:
    """Get shared rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        config = get_config()
        _rate_limiter = RateLimiterService(
            default_capacity=config.rate_limit_capacity,
            default_refill_rate=config.rate_limit_refill_rate,
        )
    return _rate_limiter


def get_api_key_service() -> APIKeyService:
    """Get shared API key service instance."""
    global _api_key_service
    if _api_key_service is None:
        _api_key_service = APIKeyService()
    return _api_key_service


def get_security_audit_log() -> SecurityAuditLog:
    """Get shared security audit log instance."""
    global _security_audit_log
    if _security_audit_log is None:
        _security_audit_log = SecurityAuditLog()
    return _security_audit_log


# ---- Request / Response Models ----

class TokenRequest(BaseModel):
    """Request model for token generation."""
    client_id: str
    expires_in_minutes: int = 60


class TokenResponse(BaseModel):
    """Response model for token endpoint."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh."""
    token: str
    expires_in_minutes: int = 60


class APIKeyCreateRequest(BaseModel):
    """Request model for API key creation."""
    client_name: str
    scopes: Optional[List[str]] = None


class APIKeyCreateResponse(BaseModel):
    """Response model for API key creation (plaintext returned once)."""
    api_key: str
    key_id: str
    client_name: str
    scopes: List[str]
    message: str = "Store this key securely. It will not be shown again."


class APIKeyListItem(BaseModel):
    """Response model for API key listing (no plaintext)."""
    key_id: str
    client_name: str
    scopes: List[str]
    created_at: str
    revoked: bool


# ---- Auth Endpoints ----

@router.post(
    "/auth/token",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
    responses={
        400: {"description": "Invalid client_id"}
    }
)
async def get_auth_token(request: TokenRequest):
    """Generate JWT authentication token.

    Args:
        request: Token request with client_id and optional expiration

    Returns:
        TokenResponse: JWT access token

    Raises:
        HTTPException: 400 if client_id is missing
    """
    if not request.client_id or not request.client_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id is required"
        )

    config = get_config()
    jwt_service = JWTService(
        secret_key=config.jwt_secret_key,
        algorithm=config.jwt_algorithm
    )

    token = jwt_service.generate_token(
        subject=request.client_id,
        expires_in_minutes=request.expires_in_minutes
    )

    # Log auth event
    audit = get_security_audit_log()
    audit.log_event(
        SecurityEventType.AUTH_SUCCESS,
        client_id=request.client_id,
        details={"method": "jwt", "expires_in_minutes": request.expires_in_minutes},
    )

    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=request.expires_in_minutes * 60
    )


@router.post(
    "/auth/refresh",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    responses={
        401: {"description": "Invalid or expired token"}
    }
)
async def refresh_auth_token(request: TokenRefreshRequest):
    """Refresh a JWT token to get a new one with extended expiration.

    The original token must still be valid (not expired).

    Args:
        request: Refresh request with existing token.

    Returns:
        TokenResponse: New JWT access token.
    """
    config = get_config()
    jwt_service = JWTService(
        secret_key=config.jwt_secret_key,
        algorithm=config.jwt_algorithm
    )

    try:
        new_token = jwt_service.refresh_token(
            token=request.token,
            expires_in_minutes=request.expires_in_minutes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return TokenResponse(
        access_token=new_token,
        token_type="Bearer",
        expires_in=request.expires_in_minutes * 60,
    )


# ---- API Key Endpoints ----

@router.post(
    "/api-keys",
    status_code=status.HTTP_201_CREATED,
    response_model=APIKeyCreateResponse,
)
async def create_api_key(
    request: APIKeyCreateRequest,
    client_id: str = Depends(verify_jwt_token),
):
    """Create a new API key. Requires JWT authentication.

    Args:
        request: API key creation request.
        client_id: Authenticated client (from JWT).

    Returns:
        APIKeyCreateResponse with plaintext key (shown once).
    """
    if not request.client_name or not request.client_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_name is required",
        )

    svc = get_api_key_service()
    scopes = set(request.scopes) if request.scopes else None
    plaintext_key, key_id = svc.generate_key(
        client_name=request.client_name,
        scopes=scopes,
    )

    audit = get_security_audit_log()
    audit.log_event(
        SecurityEventType.KEY_GENERATED,
        client_id=client_id,
        details={"key_id": key_id, "client_name": request.client_name},
    )

    record = svc._store[key_id]
    return APIKeyCreateResponse(
        api_key=plaintext_key,
        key_id=key_id,
        client_name=request.client_name,
        scopes=sorted(record.scopes),
    )


@router.get(
    "/api-keys",
    response_model=List[APIKeyListItem],
)
async def list_api_keys(
    client_id: str = Depends(verify_jwt_token),
):
    """List all active API keys."""
    svc = get_api_key_service()
    records = svc.list_keys(include_revoked=False)
    return [
        APIKeyListItem(
            key_id=r.key_id,
            client_name=r.client_name,
            scopes=sorted(r.scopes),
            created_at=r.created_at.isoformat(),
            revoked=r.revoked,
        )
        for r in records
    ]


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_200_OK,
)
async def revoke_api_key(
    key_id: str,
    client_id: str = Depends(verify_jwt_token),
):
    """Revoke an API key.

    Args:
        key_id: The key ID to revoke.
        client_id: Authenticated client (from JWT).
    """
    svc = get_api_key_service()
    try:
        svc.revoke_key(key_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    audit = get_security_audit_log()
    audit.log_event(
        SecurityEventType.KEY_REVOKED,
        client_id=client_id,
        details={"key_id": key_id},
    )

    return {"status": "revoked", "key_id": key_id}


# ---- Detection Endpoint ----

@router.post(
    "/detections",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid detection payload"},
        429: {"description": "Rate limit exceeded"},
    }
)
async def create_detection(
    detection: DetectionInput,
    request: Request,
    session: Session = Depends(get_db_session),
    client_id: str = Depends(verify_jwt_token),
):
    """Accept detection data and return CoT/TAK format.

    Ingests AI detection with image pixels and camera metadata,
    calculates geolocation via photogrammetry, and returns standard
    Cursor on Target (CoT) XML for TAK system integration.

    Includes rate limiting and security audit logging.

    Args:
        detection: Detection payload with image and pixel coordinates
        request: FastAPI request object
        session: Database session (injected dependency)
        client_id: Authenticated client (from JWT)

    Returns:
        XMLResponse: CoT XML for TAK system consumption

    Raises:
        HTTPException: 400 for invalid input, 429 for rate limit, 500 for errors
    """
    # Rate limiting
    limiter = get_rate_limiter()
    result = limiter.check_rate_limit(client_id)

    if not result.allowed:
        audit = get_security_audit_log()
        audit.log_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            client_id=client_id,
            source_ip=request.client.host if request.client else None,
            details={"retry_after": result.retry_after_seconds},
            severity="WARNING",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(int(result.retry_after_seconds) + 1),
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    try:
        # Process detection: geolocate and store
        service = DetectionService(session)
        det_result = service.accept_detection(detection)
        detection_id = det_result["detection_id"]
        geolocation = det_result["geolocation"]

        # Generate CoT XML
        config = get_config()
        cot_service = CotService(tak_server_url=config.tak_server_url)
        cot_xml = cot_service.generate_cot_xml(
            detection_id=detection_id,
            geolocation=geolocation,
            object_class=detection.object_class,
            ai_confidence=detection.ai_confidence,
            camera_id=detection.camera_id,
            timestamp=detection.timestamp,
        )

        # Push to TAK server if configured (async, non-blocking)
        try:
            import asyncio
            asyncio.create_task(cot_service.push_to_tak_server(cot_xml))
        except Exception:
            pass  # Non-critical, continue even if TAK push fails

        # Return CoT XML as primary response with rate limit headers
        return Response(
            content=cot_xml,
            status_code=status.HTTP_201_CREATED,
            media_type="application/xml",
            headers={
                "X-Detection-ID": detection_id,
                "X-Confidence-Flag": geolocation.confidence_flag,
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "E002",
                "error_message": str(e),
                "details": None,
            },
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Detection processing error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "E999",
                "error_message": f"Internal server error: {str(e)}",
                "details": None,
            },
        )
