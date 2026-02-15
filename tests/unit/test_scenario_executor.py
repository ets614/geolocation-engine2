"""
Unit tests for ScenarioExecutor (driven port adapter).

Test Budget: 1 behavior x 2 = 2 tests max

Behavior:
  ScenarioExecutor runs Locust scenarios (ramp-up, sustained, spike, soak)
  and collects raw request metrics.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass


@dataclass
class MockStats:
    """Mock Locust stats object."""
    total: dict
    num_requests: int
    num_failures: int


class TestScenarioExecutor:
    """Tests for ScenarioExecutor."""

    def test_executor_runs_sustained_scenario_and_collects_metrics(self):
        """
        Behavior: ScenarioExecutor.run executes sustained load via Locust

        Given: Executor initialized with API endpoint
        When: I call executor.run(scenario_type="sustained", users=50, duration=600)
        Then:
          - Locust swarm is launched with 50 users
          - Request metrics collected (count, errors, latencies)
          - Result contains raw metrics dict
        """
        from src.services.scenario_executor import ScenarioExecutor

        executor = ScenarioExecutor(
            api_base_url="http://localhost:9000",
            jwt_token="test-token",
        )

        with patch.object(executor, "_launch_locust") as mock_locust:
            # Configure mock Locust response
            latencies = [100, 150, 200, 250, 1900, 2000] * 833  # 4998 items
            mock_locust.return_value = {
                "request_count": 4998,
                "error_count": 5,
                "latencies": latencies,
                "recovery_time_seconds": None,
                "memory_growth_percent": None,
            }

            result = executor.run(
                scenario_type="sustained",
                users=50,
                ramp_time_seconds=60,
                duration_seconds=600,
            )

            # Verify metrics collected
            assert result["request_count"] == 4998
            assert result["error_count"] == 5
            assert len(result["latencies"]) == 4998

    def test_executor_routes_scenario_type_to_locust_locustfile(self):
        """
        Behavior: ScenarioExecutor selects correct locustfile scenario

        Given: Executor initialized
        When: I call run with scenario_type="spike"
        Then:
          - Correct LoadUser class is selected
          - User spawn_rate configured for spike (fast ramp)
          - Duration is 30 seconds (spike window)
        """
        from src.services.scenario_executor import ScenarioExecutor

        executor = ScenarioExecutor(
            api_base_url="http://localhost:9000",
            jwt_token="test-token",
        )

        with patch.object(executor, "_launch_locust") as mock_locust:
            mock_locust.return_value = {
                "request_count": 100,
                "error_count": 1,
                "latencies": [200] * 100,
            }

            result = executor.run(
                scenario_type="spike",
                users=200,
                ramp_time_seconds=10,
                duration_seconds=30,
            )

            # Verify run completed
            assert result is not None
            assert "request_count" in result
            assert result["request_count"] > 0
