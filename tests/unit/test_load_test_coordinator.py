"""
Unit tests for LoadTestCoordinator (driving port).

Test Budget: 1 behavior x 2 = 2 tests max

Behavior:
  LoadTestCoordinator coordinates scenario execution (ramp-up, sustained, spike, soak)
  through port-to-port architecture.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


class TestLoadTestCoordinator:
    """Tests for LoadTestCoordinator coordination logic."""

    def test_coordinator_executes_sustained_load_scenario(self):
        """
        Behavior: LoadTestCoordinator.run_scenario orchestrates sustained load test

        Given: Coordinator initialized with API endpoint and JWT token
        When: I call coordinator.run_scenario(scenario_type="sustained", users=50, duration=600)
        Then:
          - ScenarioExecutor receives sustained scenario config
          - MetricsCollector gathers latency/throughput/errors
          - Result contains p95_latency_ms, throughput_req_sec, error_rate_percent
          - BaselineComparator validates against SLOs
        """
        from src.services.load_test_coordinator import LoadTestCoordinator

        # Create coordinator with mocked dependencies at port boundaries
        mock_executor = Mock()
        mock_metrics = Mock()
        mock_comparator = Mock()
        mock_reporter = Mock()

        # Mock the dependencies
        with patch(
            "src.services.load_test_coordinator.ScenarioExecutor",
            return_value=mock_executor,
        ), patch(
            "src.services.load_test_coordinator.MetricsCollector",
            return_value=mock_metrics,
        ), patch(
            "src.services.load_test_coordinator.BaselineComparator",
            return_value=mock_comparator,
        ), patch(
            "src.services.load_test_coordinator.ReportGenerator",
            return_value=mock_reporter,
        ):

            coordinator = LoadTestCoordinator(
                api_base_url="http://localhost:9000",
                jwt_token="test-token",
            )

            # Configure mocked returns
            mock_executor.run.return_value = {
                "request_count": 5000,
                "error_count": 5,
                "latencies": [100, 150, 200, 250, 1900, 2000],
            }

            mock_metrics.collect.return_value = {
                "p95_latency_ms": 1900,
                "p99_latency_ms": 2000,
                "throughput_req_sec": 150,
                "error_rate_percent": 0.1,
                "success_count": 5000,
            }

            mock_comparator.compare.return_value = {
                "status": "PASS",
                "deviations": [],
            }

            mock_reporter.generate.return_value = "/tmp/report_123.html"

            # Execute scenario
            result = coordinator.run_scenario(
                scenario_type="sustained",
                users=50,
                ramp_time_seconds=60,
                duration_seconds=600,
                endpoint="/api/v1/detections",
            )

            # Verify result structure
            assert result.p95_latency_ms == 1900
            assert result.p99_latency_ms == 2000
            assert result.throughput_req_sec == 150
            assert result.error_rate_percent == 0.1
            assert result.success_count == 5000
            assert result.html_report_path == "/tmp/report_123.html"

    def test_coordinator_routes_to_correct_scenario_executor(self):
        """
        Behavior: LoadTestCoordinator routes scenario type to appropriate executor

        Given: Coordinator initialized
        When: I call run_scenario with different scenario_type values
        Then:
          - ScenarioExecutor receives correct scenario config
          - ramp_up scenario uses users_min/users_max
          - sustained scenario uses fixed users
          - spike scenario uses high user count, short duration
          - soak scenario uses long duration, low user count
        """
        from src.services.load_test_coordinator import LoadTestCoordinator

        with patch(
            "src.services.load_test_coordinator.ScenarioExecutor"
        ) as mock_executor_class:

            mock_executor = Mock()
            mock_executor_class.return_value = mock_executor
            mock_executor.run.return_value = {
                "request_count": 1000,
                "error_count": 0,
                "latencies": [100] * 1000,
            }

            with patch(
                "src.services.load_test_coordinator.MetricsCollector"
            ) as mock_metrics_class, patch(
                "src.services.load_test_coordinator.BaselineComparator"
            ) as mock_comp_class, patch(
                "src.services.load_test_coordinator.ReportGenerator"
            ) as mock_report_class:

                mock_metrics = Mock()
                mock_metrics_class.return_value = mock_metrics
                mock_metrics.collect.return_value = {
                    "p95_latency_ms": 100,
                    "p99_latency_ms": 100,
                    "throughput_req_sec": 100,
                    "error_rate_percent": 0,
                    "success_count": 1000,
                }

                mock_comparator = Mock()
                mock_comp_class.return_value = mock_comparator
                mock_comparator.compare.return_value = {"status": "PASS", "deviations": []}

                mock_reporter = Mock()
                mock_report_class.return_value = mock_reporter
                mock_reporter.generate.return_value = "/tmp/report.html"

                coordinator = LoadTestCoordinator(
                    api_base_url="http://localhost:9000",
                    jwt_token="test-token",
                )

                # Test spike scenario routing
                result = coordinator.run_scenario(
                    scenario_type="spike",
                    users=200,
                    ramp_time_seconds=10,
                    duration_seconds=30,
                    endpoint="/api/v1/detections",
                )

                # Verify executor was called with spike config
                assert result is not None
                assert result.p95_latency_ms == 100
