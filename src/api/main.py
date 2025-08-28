"""
FastAPI application entry point for metrics API service.

This module initializes and configures the main FastAPI application instance
that serves performance metrics data from the FUSE Test Data Generator monitoring
system. Provides REST API endpoints through route inclusion, CORS configuration
for React frontend integration, and global exception handling for consistent
error responses.

The application supports:
- Automatic OpenAPI documentation generation
- Cross-origin resource sharing for frontend access
- Standardized error response formats
- Async request handling for optimal performance
- Health check endpoints for service monitoring

Usage:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000
"""

import os
import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api.routes.metrics import router
from src.api.models.responses import ErrorResponse


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI application instance with metadata
app = FastAPI(
    title="FUSE Test Data Generator Metrics API",
    description="""
    REST API service for performance metrics and monitoring data from the
    FUSE Test Data Generator system.
    
    This API provides comprehensive access to:
    - Historical run performance data
    - Real-time execution metrics
    - Multi-run comparison analysis
    - Performance optimization insights
    
    Designed for integration with React frontend dashboard and automation tools.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS configuration for React frontend integration
# Allow cross-origin requests from the React development server and production builds
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://127.0.0.1:3000",  # Alternative localhost
        "http://localhost:3001",  # Alternative React port
        "http://127.0.0.1:3001",  # Alternative localhost
    ],
    allow_credentials=False,  # No authentication required for current scope
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Allow all headers for development flexibility
    max_age=3600  # Cache preflight requests for 1 hour
)

# Include metrics router with all API endpoints
app.include_router(router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global HTTP exception handler providing standardized error responses.
    
    Converts HTTPException instances to consistent ErrorResponse format
    with appropriate HTTP status codes and detailed error information.
    
    Args:
        request: FastAPI Request object with URL, method, and headers
        exc: HTTPException instance with status code and detail
        
    Returns:
        JSONResponse with ErrorResponse model structure
    """
    error_response = ErrorResponse(
        error_code=f"HTTP_{exc.status_code}",
        message=exc.detail,
        details={
            "request_url": str(request.url),
            "request_method": request.method,
            "status_code": exc.status_code,
            "headers": dict(request.headers) if hasattr(request, 'headers') else {}
        },
        timestamp=datetime.now()
    )
    
    logger.error(
        f"HTTP {exc.status_code} error on {request.method} {request.url}: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Global validation exception handler for Pydantic model errors.
    
    Processes Pydantic validation errors and converts them to standardized
    error responses with detailed validation failure information.
    
    Args:
        request: FastAPI Request object with URL, method, and headers
        exc: ValidationError instance with validation errors
        
    Returns:
        JSONResponse with ErrorResponse model structure and validation details
    """
    # Extract validation errors using the errors() method
    validation_errors = exc.errors()
    
    error_response = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details={
            "request_url": str(request.url),
            "request_method": request.method,
            "validation_errors": validation_errors,
            "error_count": len(validation_errors)
        },
        timestamp=datetime.now()
    )
    
    logger.error(
        f"Validation error on {request.method} {request.url}: {validation_errors}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions.
    
    Catches any unhandled exceptions and provides consistent error responses
    while logging the full exception details for debugging.
    
    Args:
        request: FastAPI Request object with URL, method, and headers
        exc: General Exception instance
        
    Returns:
        JSONResponse with ErrorResponse model structure
    """
    error_response = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred while processing the request",
        details={
            "request_url": str(request.url),
            "request_method": request.method,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        },
        timestamp=datetime.now()
    )
    
    logger.error(
        f"Unhandled exception on {request.method} {request.url}: {type(exc).__name__}: {str(exc)}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )


@app.on_event("startup")
async def startup_event() -> None:
    """
    Startup event handler for application initialization.
    
    Performs necessary initialization tasks when the FastAPI application starts,
    including metrics directory verification, logging configuration, and service
    health checks.
    """
    logger.info("Starting FUSE Test Data Generator Metrics API")
    logger.info(f"API Documentation available at: /docs")
    logger.info(f"Alternative documentation at: /redoc")
    
    # Verify metrics directory exists
    metrics_dir = "metrics/runs"
    if not os.path.exists(metrics_dir):
        logger.warning(f"Metrics directory not found: {metrics_dir}")
        logger.info("Metrics directory will be created automatically when data is available")
    else:
        # Count available run files
        try:
            json_files = [f for f in os.listdir(metrics_dir) 
                         if f.endswith('.json') and os.path.isfile(os.path.join(metrics_dir, f))]
            logger.info(f"Found {len(json_files)} run metrics files in storage")
        except OSError as e:
            logger.warning(f"Could not read metrics directory: {e}")
    
    logger.info("Metrics API service started successfully")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Shutdown event handler for graceful application termination.
    
    Performs cleanup tasks when the FastAPI application is shutting down,
    ensuring all resources are properly released and connections are closed.
    """
    logger.info("Shutting down FUSE Test Data Generator Metrics API")
    logger.info("Cleanup completed successfully")


@app.get(
    "/",
    summary="Service Health Check",
    description="Basic health check endpoint to verify API service availability",
    response_description="Service status and basic information",
    tags=["health"]
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint providing service status and basic information.
    
    Returns current service status, version information, and basic metrics
    about available data for monitoring and automation purposes.
    
    Returns:
        Dictionary containing service status, version, and metrics summary
    """
    # Check metrics directory status
    metrics_dir = "metrics/runs"
    available_runs = 0
    storage_status = "unavailable"
    
    try:
        if os.path.exists(metrics_dir):
            json_files = [f for f in os.listdir(metrics_dir) 
                         if f.endswith('.json') and os.path.isfile(os.path.join(metrics_dir, f))]
            available_runs = len(json_files)
            storage_status = "available"
    except OSError:
        storage_status = "error"
    
    return {
        "service": "FUSE Test Data Generator Metrics API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "metrics_storage": {
            "status": storage_status,
            "available_runs": available_runs,
            "directory": metrics_dir
        },
        "endpoints": {
            "documentation": "/docs",
            "alternative_docs": "/redoc",
            "openapi_schema": "/openapi.json",
            "runs_list": "/api/runs",
            "run_details": "/api/runs/{run_id}",
            "run_comparison": "/api/runs/compare",
            "latest_metrics": "/api/metrics/latest"
        }
    }


# The FastAPI application instance is the main export
# Required methods are automatically available through FastAPI class:
# - include_router(): Used above to include metrics endpoints
# - add_middleware(): Used above for CORS configuration  
# - exception_handler(): Used above for global error handling
# - on_event(): Used above for startup/shutdown handlers
# - get(), post(), put(), delete(): Available for additional route definitions

if __name__ == "__main__":
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )