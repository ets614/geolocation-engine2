"""API routes for detection ingestion with CoT/TAK output."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.models.schemas import DetectionInput, ErrorResponse
from src.services.detection_service import DetectionService
from src.services.cot_service import CotService
from src.services.jwt_service import JWTService
from src.database import get_db_session
from src.config import get_config
from src.api.auth import verify_jwt_token
from typing import Optional

router = APIRouter(prefix="/api/v1", tags=["detections"])


class TokenRequest(BaseModel):
    """Request model for token generation."""
    client_id: str
    expires_in_minutes: int = 60


class TokenResponse(BaseModel):
    """Response model for token endpoint."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


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

    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=request.expires_in_minutes * 60
    )


@router.post(
    "/detections",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid detection payload"}
    }
)
async def create_detection(
    detection: DetectionInput,
    session: Session = Depends(get_db_session),
    client_id: str = Depends(verify_jwt_token)
):
    """Accept detection data and return CoT/TAK format.

    Ingests AI detection with image pixels and camera metadata,
    calculates geolocation via photogrammetry, and returns standard
    Cursor on Target (CoT) XML for TAK system integration.

    Args:
        detection: Detection payload with image and pixel coordinates
        session: Database session (injected dependency)

    Returns:
        XMLResponse: CoT XML for TAK system consumption
        JSONResponse: CoT as JSON with metadata (if Accept: application/json)

    Raises:
        HTTPException: 400 for invalid input, 500 for processing errors
    """
    try:
        # Process detection: geolocate and store
        service = DetectionService(session)
        result = service.accept_detection(detection)
        detection_id = result["detection_id"]
        geolocation = result["geolocation"]

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

        # Return CoT XML as primary response
        return Response(
            content=cot_xml,
            status_code=status.HTTP_201_CREATED,
            media_type="application/xml",
            headers={
                "X-Detection-ID": detection_id,
                "X-Confidence-Flag": geolocation.confidence_flag,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "E999",
                "error_message": "Internal server error",
                "details": None,
            },
        )


class RateLimitMetricsResponse(BaseModel):
    """Rate limit metrics response."""
    quota_limit: int
    quota_used: int
    quota_remaining: int
    quota_reset_time_seconds: int


@router.get(
    "/metrics/rate-limit",
    response_model=RateLimitMetricsResponse,
    responses={
        400: {"description": "Missing or invalid client_id"},
        401: {"description": "Unauthorized"},
    }
)
async def get_rate_limit_metrics(
    request: Request,
    client_id: Optional[str] = None,
):
    """Get rate limit quota metrics for a client.

    Args:
        request: HTTP request (to access rate limiter from app state)
        client_id: Client identifier (optional, uses authenticated client if not provided)

    Returns:
        RateLimitMetricsResponse: Current quota usage and reset time

    Raises:
        HTTPException: 400 if client_id is missing, 401 if unauthorized
    """
    # Get client ID from parameter or request state
    actual_client_id = client_id or getattr(request.state, "client_id", None)

    if not actual_client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id is required",
        )

    # Get rate limiter from app state (set up by middleware)
    rate_limiter = getattr(request.app.state, "rate_limiter", None)
    if not rate_limiter:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rate limiter not configured",
        )

    # Get quota usage
    usage = rate_limiter.get_quota_usage(actual_client_id)

    return RateLimitMetricsResponse(
        quota_limit=usage["quota_limit"],
        quota_used=usage["quota_used"],
        quota_remaining=usage["quota_remaining"],
        quota_reset_time_seconds=usage["quota_reset_time_seconds"],
    )
