"""
OpenTelemetry and structured logging configuration for GST Service Center Management System.
Provides observability through distributed tracing, metrics, and structured logging.
"""

import logging
import os
from typing import Optional

import structlog
from opentelemetry import trace, metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from prometheus_client import start_http_server


def configure_observability(
    service_name: str = "gst-service-center",
    environment: str = "development",
    enable_prometheus: bool = True,
    prometheus_port: int = 8001
) -> None:
    """
    Configure OpenTelemetry tracing, metrics, and structured logging.

    Args:
        service_name: Name of the service for tracing
        environment: Environment (development, staging, production)
        enable_prometheus: Whether to enable Prometheus metrics
        prometheus_port: Port for Prometheus metrics endpoint
    """

    # Configure structured logging
    configure_structured_logging(service_name, environment)

    # Configure OpenTelemetry tracing
    configure_tracing(service_name, environment)

    # Configure metrics with Prometheus
    if enable_prometheus:
        configure_metrics(prometheus_port)

    logger = structlog.get_logger()
    logger.info(
        "Observability configured",
        service_name=service_name,
        environment=environment,
        prometheus_enabled=enable_prometheus,
        prometheus_port=prometheus_port if enable_prometheus else None
    )


def configure_structured_logging(service_name: str, environment: str) -> None:
    """Configure structured logging with JSON output for production."""

    # Determine log level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Configure timestamp formatting
    timestamper = structlog.processors.TimeStamper(fmt="ISO")

    # Shared processors for all environments
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if environment == "development":
        # Pretty console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
        formatter = None
    else:
        # JSON output for production
        processors = shared_processors + [
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ]
        formatter = logging.Formatter('%(message)s')

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s" if environment != "development" else None,
        level=getattr(logging, log_level),
        handlers=[logging.StreamHandler()]
    )

    # Add service context to all logs
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        service_name=service_name,
        environment=environment
    )


def configure_tracing(service_name: str, environment: str) -> None:
    """Configure OpenTelemetry distributed tracing."""

    # Create resource with service information
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "environment": environment,
        "deployment.type": "container"
    })

    # Initialize tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Add console exporter for development
    if environment == "development":
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(span_processor)

    # TODO: Add OTLP exporter for production (Azure Monitor, Jaeger, etc.)
    # if environment == "production":
    #     from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    #     otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:14250")
    #     tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))


def configure_metrics(prometheus_port: int) -> None:
    """Configure OpenTelemetry metrics with Prometheus export."""

    # Create Prometheus metric reader
    prometheus_reader = PrometheusMetricReader()

    # Initialize meter provider
    meter_provider = MeterProvider(
        metric_readers=[prometheus_reader]
    )
    metrics.set_meter_provider(meter_provider)

    # Start Prometheus HTTP server
    start_http_server(prometheus_port)


def instrument_fastapi(app) -> None:
    """Instrument FastAPI application with OpenTelemetry."""
    FastAPIInstrumentor.instrument_app(app)


def instrument_sqlalchemy(engine) -> None:
    """Instrument SQLAlchemy engine with OpenTelemetry."""
    SQLAlchemyInstrumentor().instrument(engine=engine)


def get_tracer(name: str) -> trace.Tracer:
    """Get OpenTelemetry tracer for manual instrumentation."""
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get OpenTelemetry meter for custom metrics."""
    return metrics.get_meter(name)


# Custom context manager for tracing business operations
class trace_operation:
    """Context manager for tracing business operations with structured logging."""

    def __init__(self, operation_name: str, **attributes):
        self.operation_name = operation_name
        self.attributes = attributes
        self.tracer = get_tracer(__name__)
        self.logger = structlog.get_logger()
        self.span: Optional[trace.Span] = None

    def __enter__(self):
        self.span = self.tracer.start_span(
            self.operation_name,
            attributes=self.attributes
        )

        self.logger.info(
            "Operation started",
            operation=self.operation_name,
            **self.attributes
        )

        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Log and record exception in span
            self.logger.error(
                "Operation failed",
                operation=self.operation_name,
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.attributes
            )

            if self.span:
                self.span.record_exception(exc_val)
                self.span.set_status(trace.Status(
                    trace.StatusCode.ERROR, str(exc_val)))
        else:
            self.logger.info(
                "Operation completed",
                operation=self.operation_name,
                **self.attributes
            )

            if self.span:
                self.span.set_status(trace.Status(trace.StatusCode.OK))

        if self.span:
            self.span.end()


# Performance monitoring utilities
class PerformanceMonitor:
    """Utility class for monitoring API performance and constitutional compliance."""

    def __init__(self):
        self.meter = get_meter(__name__)
        self.request_duration = self.meter.create_histogram(
            name="api_request_duration_ms",
            description="API request duration in milliseconds",
            unit="ms"
        )
        self.request_count = self.meter.create_counter(
            name="api_request_count",
            description="Total number of API requests"
        )
        self.gst_calculation_duration = self.meter.create_histogram(
            name="gst_calculation_duration_ms",
            description="GST calculation duration in milliseconds",
            unit="ms"
        )

    def record_request(self, endpoint: str, method: str, duration_ms: float, status_code: int):
        """Record API request metrics."""
        attributes = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        }

        self.request_duration.record(duration_ms, attributes)
        self.request_count.add(1, attributes)

        # Log warning if response time exceeds constitutional requirement (200ms)
        if duration_ms > 200:
            logger = structlog.get_logger()
            logger.warning(
                "API response time exceeded constitutional requirement",
                endpoint=endpoint,
                method=method,
                duration_ms=duration_ms,
                constitutional_limit_ms=200
            )

    def record_gst_calculation(self, calculation_type: str, duration_ms: float):
        """Record GST calculation performance."""
        self.gst_calculation_duration.record(
            duration_ms,
            {"calculation_type": calculation_type}
        )


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
