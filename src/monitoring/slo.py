"""Service Level Objectives (SLO) definitions and tracking."""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class SLOType(Enum):
    """Types of SLOs."""

    AVAILABILITY = "availability"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


@dataclass
class SLO:
    """Service Level Objective definition."""

    name: str
    description: str
    slo_type: SLOType
    target: float
    measurement_window: str
    error_budget_percentage: float

    def get_error_budget(self) -> float:
        """Calculate error budget percentage.

        Returns:
            Error budget as percentage of measurement window.
        """
        return (100.0 - self.target) * (self.error_budget_percentage / 100.0)


# SLOs for Detection API
AVAILABILITY_SLO = SLO(
    name="API Availability",
    description="Percentage of time API responds without errors",
    slo_type=SLOType.AVAILABILITY,
    target=99.5,
    measurement_window="30d",
    error_budget_percentage=100.0,
)

LATENCY_P95_SLO = SLO(
    name="Request Latency P95",
    description="95th percentile request latency",
    slo_type=SLOType.LATENCY,
    target=99.0,  # 99% of requests under 2 seconds
    measurement_window="30d",
    error_budget_percentage=100.0,
)

LATENCY_P99_SLO = SLO(
    name="Request Latency P99",
    description="99th percentile request latency",
    slo_type=SLOType.LATENCY,
    target=99.0,  # 99% of requests under 5 seconds
    measurement_window="30d",
    error_budget_percentage=100.0,
)

ERROR_RATE_SLO = SLO(
    name="Error Rate",
    description="Percentage of requests that complete successfully",
    slo_type=SLOType.ERROR_RATE,
    target=99.9,
    measurement_window="30d",
    error_budget_percentage=100.0,
)

THROUGHPUT_SLO = SLO(
    name="Detection Processing Throughput",
    description="Detections processed per second",
    slo_type=SLOType.THROUGHPUT,
    target=1000,  # 1000 detections per second
    measurement_window="30d",
    error_budget_percentage=100.0,
)

# SLO Summary
SLO_DEFINITIONS = [
    AVAILABILITY_SLO,
    LATENCY_P95_SLO,
    LATENCY_P99_SLO,
    ERROR_RATE_SLO,
    THROUGHPUT_SLO,
]


class SLOTracker:
    """Tracks SLO compliance over time."""

    def __init__(self, slo: SLO):
        """Initialize SLO tracker.

        Args:
            slo: SLO definition.
        """
        self.slo = slo
        self.measurements = []
        self.violations = 0
        self.total_measurements = 0

    def record_measurement(self, value: float, timestamp: Optional[float] = None):
        """Record a measurement.

        Args:
            value: Measured value.
            timestamp: Measurement timestamp.
        """
        self.measurements.append({"value": value, "timestamp": timestamp})
        self.total_measurements += 1

    def check_compliance(self, value: float) -> bool:
        """Check if value is within SLO target.

        Args:
            value: Value to check.

        Returns:
            True if compliant, False otherwise.
        """
        compliant = value <= self.slo.target if self.slo.slo_type == SLOType.LATENCY else value >= self.slo.target

        if not compliant:
            self.violations += 1

        return compliant

    def get_compliance_percentage(self) -> float:
        """Calculate compliance percentage.

        Returns:
            Compliance as percentage (0-100).
        """
        if self.total_measurements == 0:
            return 100.0

        return ((self.total_measurements - self.violations) / self.total_measurements) * 100

    def get_error_budget_remaining(self) -> float:
        """Calculate remaining error budget.

        Returns:
            Remaining error budget in measurements.
        """
        if self.total_measurements == 0:
            return 0

        error_budget = self.slo.get_error_budget()
        allowed_violations = int((self.total_measurements * error_budget) / 100)
        return max(0, allowed_violations - self.violations)


# Alert thresholds based on SLOs
ALERT_THRESHOLDS = {
    "error_rate_critical": 1.0,  # >1% error rate
    "latency_p95_warning": 2.0,  # >2 seconds for p95
    "latency_p95_critical": 5.0,  # >5 seconds for p95
    "latency_p99_warning": 5.0,  # >5 seconds for p99
    "latency_p99_critical": 10.0,  # >10 seconds for p99
    "availability_warning": 99.0,  # <99% availability
    "availability_critical": 98.0,  # <98% availability
}
