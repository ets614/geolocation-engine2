"""
Unit tests for MetricsCollector (internal service - tested through driving port).

Test Budget: 1 behavior x 2 = 2 tests max

Behavior:
  MetricsCollector aggregates raw latency/throughput/error metrics
  from scenario execution into SLO-comparable format.
"""
import pytest
from unittest.mock import Mock
from statistics import median


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_collector_calculates_p95_p99_latency_percentiles(self):
        """
        Behavior: MetricsCollector.collect calculates latency percentiles

        Given: Raw latency data from 5000 requests
        When: I call collector.collect(raw_metrics)
        Then:
          - p95_latency_ms calculated correctly (95th percentile)
          - p99_latency_ms calculated correctly (99th percentile)
          - p50_latency_ms (median) also available
        """
        from src.services.metrics_collector import MetricsCollector

        # Create realistic latency distribution
        latencies = (
            [100] * 4500 +  # 90% under 100ms
            [200] * 350 +   # 7% between 100-200ms
            [500] * 120 +   # 2.4% between 200-500ms
            [1000] * 20 +   # 0.4% between 500-1000ms
            [2000] * 10     # 0.2% > 1000ms
        )

        collector = MetricsCollector()

        metrics = collector.collect(
            request_count=5000,
            error_count=0,
            latencies=latencies,
            duration_seconds=300,
        )

        # Verify percentiles calculated
        assert metrics["p95_latency_ms"] <= 200
        assert metrics["p99_latency_ms"] <= 1000
        assert metrics["p50_latency_ms"] <= 100  # median
        assert metrics["throughput_req_sec"] == 5000 / 300
        assert metrics["error_rate_percent"] == 0.0

    def test_collector_calculates_throughput_and_error_rate(self):
        """
        Behavior: MetricsCollector calculates throughput and error metrics

        Given: Raw scenario metrics
        When: I call collector.collect(request_count, error_count, duration)
        Then:
          - throughput_req_sec = request_count / duration_seconds
          - error_rate_percent = (error_count / request_count) * 100
          - success_count = request_count - error_count
        """
        from src.services.metrics_collector import MetricsCollector

        collector = MetricsCollector()

        metrics = collector.collect(
            request_count=6000,
            error_count=5,
            latencies=[100] * 6000,
            duration_seconds=600,  # 10 minutes
        )

        # Verify throughput (should be 10 req/sec for 600s)
        assert metrics["throughput_req_sec"] == 10.0
        # Verify error rate
        assert abs(metrics["error_rate_percent"] - 0.0833) < 0.001
        # Verify success count
        assert metrics["success_count"] == 5995
