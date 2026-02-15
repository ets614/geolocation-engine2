"""API routes for detection ingestion (driving port)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.models.schemas import DetectionInput, ErrorResponse
from src.services.detection_service import DetectionService
from src.database import get_db_session

router = APIRouter(prefix="/api/v1", tags=["detections"])


@router.post(
    "/detections",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid detection payload"
        }
    }
)
async def create_detection(
    detection: DetectionInput,
    session: Session = Depends(get_db_session)
):
    """Accept detection data from external systems.

    Args:
        detection: Detection payload validated against DetectionInput schema
        session: Database session (injected dependency)

    Returns:
        dict: Contains detection_id and status code 201

    Raises:
        HTTPException: 400 for invalid input
    """
    try:
        service = DetectionService(session)
        detection_id = service.accept_detection(detection)
        return {
            "detection_id": detection_id,
            "status": "CREATED"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "E002",
                "error_message": str(e),
                "details": None
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "E999",
                "error_message": "Internal server error",
                "details": None
            }
        )
