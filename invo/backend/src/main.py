"""
FastAPI application factory and configuration.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time

from .config.database import (
    create_database_tables_async,
    check_async_database_connection,
    async_database_health_check
)
from .config.observability import setup_observability, trace_operation, PerformanceMonitor


logger = logging.getLogger(__name__)


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce constitutional requirement of <200ms response times."""

    async def dispatch(self, request: Request, call_next):
        """Process request and validate response time."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate response time
        process_time = time.time() - start_time
        response_time_ms = process_time * 1000

        # Add response time header
        response.headers["X-Response-Time"] = f"{response_time_ms:.1f}ms"

        # Log slow responses (constitutional requirement: <200ms)
        if response_time_ms > 200:
            logger.warning(
                f"Constitutional violation: Response time {response_time_ms:.1f}ms exceeds 200ms limit "
                f"for {request.method} {request.url.path}"
            )

        # Also log any response over 100ms as a warning
        elif response_time_ms > 100:
            logger.info(
                f"Slow response: {response_time_ms:.1f}ms for {request.method} {request.url.path}"
            )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting up Invoice System API...")

    try:
        # Setup observability
        setup_observability()
        logger.info("Observability setup complete")

        # Check database connection
        db_connected = await check_async_database_connection()
        if not db_connected:
            logger.error("Failed to connect to database")
            raise RuntimeError("Database connection failed")

        # Create database tables
        await create_database_tables_async()
        logger.info("Database tables verified/created")

        logger.info("Application startup complete")

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Invoice System API...")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="GST Compliant Service Center Management System",
        description="A comprehensive invoicing and inventory management system for service centers",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan
    )

    # Add middleware
    setup_middleware(app)

    # Add exception handlers
    setup_exception_handlers(app)

    # Include routers
    setup_routes(app)

    return app


def setup_middleware(app: FastAPI) -> None:
    """Setup application middleware."""

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware for production
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure appropriately for production
    )

    # Response time monitoring middleware (constitutional requirement)
    app.add_middleware(ResponseTimeMiddleware)


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup global exception handlers."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors with standardized response."""
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors()
                },
                "timestamp": time.time(),
                "path": str(request.url.path)
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with standardized response."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error": {
                    "code": getattr(exc, 'code', 'HTTP_ERROR'),
                    "message": exc.detail
                },
                "timestamp": time.time(),
                "path": str(request.url.path)
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle Starlette HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail
                },
                "timestamp": time.time(),
                "path": str(request.url.path)
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred"
                },
                "timestamp": time.time(),
                "path": str(request.url.path)
            }
        )


def setup_routes(app: FastAPI) -> None:
    """Setup application routes."""

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        with trace_operation("health_check"):
            db_health = await async_database_health_check()

            return {
                "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
                "timestamp": time.time(),
                "database": db_health,
                "version": "1.0.0"
            }

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "status": "success",
            "data": {
                "message": "GST Compliant Service Center Management System",
                "version": "1.0.0",
                "docs": "/docs",
                "health": "/health"
            },
            "timestamp": time.time()
        }

    # Metrics endpoint for monitoring
    @app.get("/metrics")
    async def metrics():
        """Basic metrics endpoint."""
        with trace_operation("metrics"):
            # Get performance metrics
            monitor = PerformanceMonitor()

            # Get database health
            db_health = await async_database_health_check()

            return {
                "status": "success",
                "data": {
                    "uptime": time.time(),  # This would be calculated properly in production
                    "database": db_health,
                    "performance": {
                        "avg_response_time": monitor.avg_response_time,
                        "request_count": monitor.request_count,
                        "error_count": monitor.error_count
                    }
                },
                "timestamp": time.time()
            }

    # Include API routers
    # Note: These routers don't exist yet - they'll be created during implementation
    # app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    # app.include_router(customer_router, prefix="/api/v1/customers", tags=["Customers"])
    # app.include_router(inventory_router, prefix="/api/v1/inventory", tags=["Inventory"])
    # app.include_router(order_router, prefix="/api/v1/orders", tags=["Orders"])
    # app.include_router(invoice_router, prefix="/api/v1/invoices", tags=["Invoices"])
    # app.include_router(report_router, prefix="/api/v1/reports", tags=["Reports"])


# Create the application instance
app = create_application()


# Export for use in other modules
__all__ = ["app", "create_application"]
