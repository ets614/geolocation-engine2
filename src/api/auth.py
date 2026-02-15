"""Authentication utilities for API endpoints."""
from fastapi import HTTPException, status, Header
from typing import Optional
from src.services.jwt_service import JWTService
from src.config import get_config


async def verify_jwt_token(
    authorization: Optional[str] = Header(None)
) -> str:
    """Verify JWT token from Authorization header.

    Args:
        authorization: Authorization header value (Bearer <token>)

    Returns:
        str: Subject claim from token

    Raises:
        HTTPException: 401 if token missing or invalid, 403 if expired
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    config = get_config()
    jwt_service = JWTService(
        secret_key=config.jwt_secret_key,
        algorithm=config.jwt_algorithm
    )

    try:
        payload = jwt_service.verify_token(token)
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return subject
    except ValueError as e:
        if "expired" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
