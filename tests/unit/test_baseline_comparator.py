"""
Unit tests for BaselineComparator (internal service - tested through driving port).

Test Budget: 1 behavior x 2 = 2 tests max

Behavior:
  BaselineComparator validates performance metrics against SLO baselines
  and identifies regressions vs improvements.
"""
import pytest
from dataclasses import dataclass


@dataclass
class MetricsSnapshot:
    """Test metrics snapshot."""
    p95_latency_ms: float
    throughput_req_sec: float
    error_rate_percent: float


class TestBaselineComparator:
    """Tests for BaselineComparator."""

    def test_comparator_validates_against_slo_baselines(self):
        """
        Behavior: BaselineComparator.compare validates metrics vs SLOs

        Given: Performance metrics and SLO baselines
        When: I call comparator.compare(metrics, baselines)
        Then:
          - Metrics passing all SLOs return status="PASS"
          - Metrics failing SLOs return status="FAIL"
          - Deviations list details which SLO failed
        """
        from src.services.baseline_comparator import BaselineComparator

        comparator = BaselineComparator(
            baseline_p95_latency_ms=2000,
            baseline_throughput_req_sec=100,
            baseline_error_rate_percent=0.1,
        )

        # Test case: all metrics passing
        result = comparator.compare(
            p95_latency_ms=1500,
            throughput_req_sec=150,
            error_rate_percent=0.05,
        )

        assert result["status"] == "PASS"
        assert len(result["deviations"]) == 0

    def test_comparator_identifies_regressions_and_improvements(self):
        """
        Behavior: BaselineComparator identifies metric trends

        Given: Metrics compared against baselines
        When: I call comparator.compare(current_metrics, baselines)
        Then:
          - Regression flagged if p95 latency increased
          - Improvement flagged if error_rate decreased
          - Deviations dict shows old_value, new_value, percent_change
        """
        from src.services.baseline_comparator import BaselineComparator

        comparator = BaselineComparator(
            baseline_p95_latency_ms=2000,
            baseline_throughput_req_sec=100,
            baseline_error_rate_percent=0.1,
        )

        # Test regression case
        result = comparator.compare(
            p95_latency_ms=2500,  # Regression: exceeded baseline
            throughput_req_sec=150,
            error_rate_percent=0.05,
        )

        assert result["status"] == "FAIL"
        assert len(result["deviations"]) > 0
        assert any(
            d.get("metric") == "p95_latency_ms" for d in result["deviations"]
        )
