"""Jaeger tracing integration for distributed tracing."""
from jaeger_client import Config as JaegerConfig
from jaeger_client.tracer import Tracer
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from typing import Optional


class JaegerTracingConfig:
    """Configuration for Jaeger tracing."""

    def __init__(
        self,
        service_name: str = "detection-api",
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        sampler_type: str = "const",
        sampler_param: float = 1.0,
    ):
        """Initialize Jaeger tracing config.

        Args:
            service_name: Service name for tracing.
            jaeger_host: Jaeger agent host.
            jaeger_port: Jaeger agent port.
            sampler_type: Sampler type (const, probabilistic, ratelimiting, remote).
            sampler_param: Sampler parameter.
        """
        self.service_name = service_name
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.sampler_type = sampler_type
        self.sampler_param = sampler_param

    def initialize_tracer(self) -> Optional[Tracer]:
        """Initialize and return Jaeger tracer.

        Returns:
            Jaeger Tracer instance or None if initialization fails.
        """
        try:
            config = JaegerConfig(
                config={
                    "sampler": {
                        "type": self.sampler_type,
                        "param": self.sampler_param,
                    },
                    "local_agent": {
                        "reporting_host": self.jaeger_host,
                        "reporting_port": self.jaeger_port,
                    },
                    "logging": True,
                },
                service_name=self.service_name,
                validate=True,
            )
            return config.initialize_tracer()
        except Exception as e:
            print(f"Failed to initialize Jaeger tracer: {e}")
            return None

    def initialize_otel_tracer(self):
        """Initialize OpenTelemetry tracer with Jaeger exporter.

        Returns:
            TracerProvider instance.
        """
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.jaeger_host,
                agent_port=self.jaeger_port,
            )

            trace_provider = TracerProvider()
            trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            trace.set_tracer_provider(trace_provider)

            return trace_provider
        except Exception as e:
            print(f"Failed to initialize OpenTelemetry tracer: {e}")
            return None


def setup_tracing(service_name: str = "detection-api"):
    """Set up distributed tracing with Jaeger and OpenTelemetry.

    Args:
        service_name: Service name for tracing.

    Returns:
        Tuple of (tracer, trace_provider).
    """
    config = JaegerTracingConfig(service_name=service_name)

    # Initialize OTel tracer
    trace_provider = config.initialize_otel_tracer()

    # Set up auto-instrumentation
    if trace_provider:
        FastAPIInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()
        RequestsInstrumentor().instrument()

    return trace.get_tracer(__name__), trace_provider


class TracingContext:
    """Context manager for manual span creation."""

    def __init__(self, span_name: str, attributes: Optional[dict] = None):
        """Initialize tracing context.

        Args:
            span_name: Name of the span.
            attributes: Optional span attributes.
        """
        self.span_name = span_name
        self.attributes = attributes or {}
        self.span = None
        self.tracer = trace.get_tracer(__name__)

    def __enter__(self):
        """Start tracing span."""
        self.span = self.tracer.start_as_current_span(self.span_name)
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End tracing span."""
        if self.span:
            if exc_type:
                self.span.set_attribute("error", True)
                self.span.set_attribute("error.type", exc_type.__name__)
            self.span.end()
        return False
