"""Unit tests for SLO (Service Level Objective) tracking."""
import pytest
from src.monitoring.slo import (
    SLO,
    SLOType,
    SLOTracker,
    AVAILABILITY_SLO,
    LATENCY_P95_SLO,
    LATENCY_P99_SLO,
    ERROR_RATE_SLO,
    THROUGHPUT_SLO,
    SLO_DEFINITIONS,
    ALERT_THRESHOLDS,
)


class TestSLODefinition:
    """Test SLO definition and creation."""

    def test_availability_slo_created(self):
        """Test availability SLO is properly defined."""
        assert AVAILABILITY_SLO.name == "API Availability"
        assert AVAILABILITY_SLO.target == 99.5
        assert AVAILABILITY_SLO.slo_type == SLOType.AVAILABILITY

    def test_latency_p95_slo_created(self):
        """Test latency P95 SLO is properly defined."""
        assert LATENCY_P95_SLO.name == "Request Latency P95"
        assert LATENCY_P95_SLO.target == 99.0
        assert LATENCY_P95_SLO.slo_type == SLOType.LATENCY

    def test_latency_p99_slo_created(self):
        """Test latency P99 SLO is properly defined."""
        assert LATENCY_P99_SLO.name == "Request Latency P99"
        assert LATENCY_P99_SLO.target == 99.0

    def test_error_rate_slo_created(self):
        """Test error rate SLO is properly defined."""
        assert ERROR_RATE_SLO.name == "Error Rate"
        assert ERROR_RATE_SLO.target == 99.9
        assert ERROR_RATE_SLO.slo_type == SLOType.ERROR_RATE

    def test_throughput_slo_created(self):
        """Test throughput SLO is properly defined."""
        assert THROUGHPUT_SLO.name == "Detection Processing Throughput"
        assert THROUGHPUT_SLO.target == 1000
        assert THROUGHPUT_SLO.slo_type == SLOType.THROUGHPUT

    def test_slo_definitions_list_not_empty(self):
        """Test SLO definitions list is not empty."""
        assert len(SLO_DEFINITIONS) > 0
        assert AVAILABILITY_SLO in SLO_DEFINITIONS
        assert ERROR_RATE_SLO in SLO_DEFINITIONS


class TestSLOErrorBudget:
    """Test error budget calculations."""

    def test_availability_error_budget(self):
        """Test error budget calculation for availability SLO."""
        error_budget = AVAILABILITY_SLO.get_error_budget()
        # 99.5% availability = 0.5% error budget
        assert error_budget == 0.5

    def test_error_rate_error_budget(self):
        """Test error budget calculation for error rate SLO."""
        error_budget = ERROR_RATE_SLO.get_error_budget()
        # 99.9% success = 0.1% error budget
        assert error_budget == 0.1

    def test_error_budget_with_partial_percentage(self):
        """Test error budget with partial percentage."""
        slo = SLO(
            name="Test SLO",
            description="Test",
            slo_type=SLOType.AVAILABILITY,
            target=99.0,
            measurement_window="30d",
            error_budget_percentage=50.0,
        )
        error_budget = slo.get_error_budget()
        # 99% availability, 50% budget = 0.5% total error budget
        assert error_budget == 0.5


class TestSLOTracker:
    """Test SLO tracker for compliance monitoring."""

    def test_tracker_initialization(self):
        """Test SLO tracker initialization."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        assert tracker.slo == AVAILABILITY_SLO
        assert tracker.violations == 0
        assert tracker.total_measurements == 0

    def test_record_single_measurement(self):
        """Test recording a single measurement."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        tracker.record_measurement(99.8)
        assert tracker.total_measurements == 1

    def test_record_multiple_measurements(self):
        """Test recording multiple measurements."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        for i in range(100):
            tracker.record_measurement(99.5 + (i % 2) * 0.2)
        assert tracker.total_measurements == 100

    def test_check_compliance_latency_below_threshold(self):
        """Test compliance check for latency below threshold."""
        tracker = SLOTracker(LATENCY_P95_SLO)
        # Target is 99%, so we're checking values
        result = tracker.check_compliance(1.5)
        assert result is True

    def test_check_compliance_latency_above_threshold(self):
        """Test compliance check for latency above threshold."""
        tracker = SLOTracker(LATENCY_P95_SLO)
        result = tracker.check_compliance(100.0)
        assert result is False
        assert tracker.violations == 1

    def test_check_compliance_availability_above_target(self):
        """Test compliance for availability above target."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        result = tracker.check_compliance(99.8)
        assert result is True

    def test_check_compliance_availability_below_target(self):
        """Test compliance for availability below target."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        result = tracker.check_compliance(99.0)
        assert result is False
        assert tracker.violations == 1

    def test_compliance_percentage_no_measurements(self):
        """Test compliance percentage with no measurements."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        compliance = tracker.get_compliance_percentage()
        assert compliance == 100.0

    def test_compliance_percentage_all_compliant(self):
        """Test compliance percentage with all compliant measurements."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        for _ in range(100):
            tracker.check_compliance(99.8)
        compliance = tracker.get_compliance_percentage()
        assert compliance == 100.0

    def test_compliance_percentage_partial_violations(self):
        """Test compliance percentage with some violations."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        for _ in range(95):
            tracker.check_compliance(99.8)
        for _ in range(5):
            tracker.check_compliance(98.0)
        compliance = tracker.get_compliance_percentage()
        assert compliance == 95.0

    def test_error_budget_remaining_no_violations(self):
        """Test error budget remaining with no violations."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        for _ in range(100):
            tracker.record_measurement(99.8)
            tracker.check_compliance(99.8)
        # With 99.5% target, 0.5% error budget
        # 100 measurements = 0.5 allowed violations
        remaining = tracker.get_error_budget_remaining()
        assert remaining >= 0

    def test_error_budget_remaining_with_violations(self):
        """Test error budget remaining when budget is consumed."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        for _ in range(100):
            tracker.record_measurement(98.0)
            tracker.check_compliance(98.0)
        # Many violations, budget likely consumed
        remaining = tracker.get_error_budget_remaining()
        assert remaining == 0


class TestSLOTypes:
    """Test different SLO types."""

    def test_slo_type_availability(self):
        """Test availability SLO type."""
        assert SLOType.AVAILABILITY.value == "availability"

    def test_slo_type_latency(self):
        """Test latency SLO type."""
        assert SLOType.LATENCY.value == "latency"

    def test_slo_type_error_rate(self):
        """Test error rate SLO type."""
        assert SLOType.ERROR_RATE.value == "error_rate"

    def test_slo_type_throughput(self):
        """Test throughput SLO type."""
        assert SLOType.THROUGHPUT.value == "throughput"


class TestAlertThresholds:
    """Test alert threshold definitions."""

    def test_error_rate_critical_threshold(self):
        """Test critical error rate threshold."""
        assert ALERT_THRESHOLDS["error_rate_critical"] == 1.0

    def test_latency_p95_thresholds(self):
        """Test P95 latency thresholds."""
        assert ALERT_THRESHOLDS["latency_p95_warning"] == 2.0
        assert ALERT_THRESHOLDS["latency_p95_critical"] == 5.0

    def test_latency_p99_thresholds(self):
        """Test P99 latency thresholds."""
        assert ALERT_THRESHOLDS["latency_p99_warning"] == 5.0
        assert ALERT_THRESHOLDS["latency_p99_critical"] == 10.0

    def test_availability_thresholds(self):
        """Test availability thresholds."""
        assert ALERT_THRESHOLDS["availability_warning"] == 99.0
        assert ALERT_THRESHOLDS["availability_critical"] == 98.0


class TestSLOComplexScenarios:
    """Test complex SLO scenarios."""

    def test_slo_tracking_with_mixed_compliance(self):
        """Test SLO tracking with alternating compliance."""
        tracker = SLOTracker(AVAILABILITY_SLO)
        measurements = [99.8, 98.5, 99.8, 98.0, 99.8, 99.2, 99.8, 99.1]
        for measurement in measurements:
            tracker.record_measurement(measurement)
            tracker.check_compliance(measurement)

        compliance = tracker.get_compliance_percentage()
        assert 0 <= compliance <= 100

    def test_multiple_slo_trackers_independent(self):
        """Test that multiple SLO trackers are independent."""
        tracker1 = SLOTracker(AVAILABILITY_SLO)
        tracker2 = SLOTracker(ERROR_RATE_SLO)

        tracker1.record_measurement(99.8)
        tracker1.check_compliance(99.8)

        tracker2.record_measurement(99.95)
        tracker2.check_compliance(99.95)

        assert tracker1.total_measurements == 1
        assert tracker2.total_measurements == 1
        assert tracker1.violations == 0
        assert tracker2.violations == 0

    def test_slo_with_custom_parameters(self):
        """Test creating SLO with custom parameters."""
        custom_slo = SLO(
            name="Custom SLO",
            description="Test custom SLO",
            slo_type=SLOType.LATENCY,
            target=250,
            measurement_window="7d",
            error_budget_percentage=100.0,
        )
        assert custom_slo.target == 250
        assert custom_slo.measurement_window == "7d"

        tracker = SLOTracker(custom_slo)
        tracker.check_compliance(200)
        assert tracker.violations == 0

        tracker.check_compliance(300)
        assert tracker.violations == 1
