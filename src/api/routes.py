"""API routes for detection ingestion with CoT/TAK output."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from src.models.schemas import DetectionInput, ErrorResponse
from src.services.detection_service import DetectionService
from src.services.cot_service import CotService
from src.database import get_db_session
from src.config import get_config

router = APIRouter(prefix="/api/v1", tags=["detections"])


@router.post(
    "/detections",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid detection payload"},
    }
)
async def create_detection(
    detection: DetectionInput,
    session: Session = Depends(get_db_session),
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

    Raises:
        HTTPException: 400 for invalid input, 500 for errors
    """
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


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "running",
        "version": "1.0.0",
        "service": "Detection to COP"
    }
