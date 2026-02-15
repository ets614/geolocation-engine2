"""FastAPI application for Detection to COP integration."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.config import get_config
from src.middleware import setup_middleware

# Create FastAPI app
config = get_config()
app = FastAPI(
    title=config.app_title,
    version=config.app_version,
    description="Service for detection to COP integration",
)

# Setup middleware
setup_middleware(app, config)


# Health check endpoint
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Service status object.
    """
    return {
        "status": "running",
        "version": config.app_version,
        "service": config.app_title,
    }


# Error handlers
@app.exception_handler(400)
async def bad_request_handler(request: Request, exc: Exception):
    """Handle 400 Bad Request errors."""
    return JSONResponse(
        status_code=400,
        content={"detail": "Bad request"},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    """Handle 404 Not Found errors."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Not found"},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle 500 Internal Server Error."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
