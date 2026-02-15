"""
LoadTestCoordinator - Orchestrates load testing scenarios (driving port).

Coordinates scenario execution through:
  - ScenarioExecutor: Runs Locust load scenarios
  - MetricsCollector: Aggregates performance metrics
  - BaselineComparator: Validates against SLO baselines
  - ReportGenerator: Creates HTML comparison reports
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from src.services.scenario_executor import ScenarioExecutor
from src.services.metrics_collector import MetricsCollector
from src.services.baseline_comparator import BaselineComparator
from src.services.report_generator import ReportGenerator


@dataclass
class LoadTestResult:
    """Result from load test scenario execution."""
    scenario_type: str
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_req_sec: float
    error_rate_percent: float
    error_count: int
    success_count: int
    request_count: int
    comparison_status: str
    deviations: list
    html_report_path: Optional[str] = None
    recovery_time_seconds: Optional[float] = None
    memory_growth_percent: Optional[float] = None


class LoadTestCoordinator:
    """Coordinates load test execution and reporting."""

    def __init__(
        self,
        api_base_url: str,
        jwt_token: str,
        output_dir: str = "/tmp/load_test_reports",
    ):
        """Initialize coordinator with API endpoint and credentials.

        Args:
            api_base_url: Base URL for API under test (e.g., http://localhost:9000)
            jwt_token: JWT authentication token for API requests
            output_dir: Directory for HTML reports
        """
        self.api_base_url = api_base_url
        self.jwt_token = jwt_token
        self.output_dir = output_dir

        # Initialize port adapters
        self.executor = ScenarioExecutor(api_base_url, jwt_token)
        self.metrics_collector = MetricsCollector()
        self.reporter = ReportGenerator(output_dir)

        # Define SLO baselines (configurable)
        self.baselines = {
            "p95_latency_ms": 2000,
            "throughput_req_sec": 100,
            "error_rate_percent": 0.1,
        }

    def run_scenario(
        self,
        scenario_type: str,
        endpoint: str = "/api/v1/detections",
        users: int = 50,
        users_min: Optional[int] = None,
        users_max: Optional[int] = None,
        ramp_time_seconds: int = 60,
        duration_seconds: int = 300,
    ) -> LoadTestResult:
        """Execute load test scenario and generate report.

        Args:
            scenario_type: "ramp_up", "sustained", "spike", or "soak"
            endpoint: API endpoint to test
            users: Number of concurrent users (sustained/soak)
            users_min: Min users for ramp_up scenario
            users_max: Max users for ramp_up scenario
            ramp_time_seconds: Time to ramp up users
            duration_seconds: Total scenario duration

        Returns:
            LoadTestResult with metrics, comparison status, and report path
        """
        # Phase 1: Execute scenario via ScenarioExecutor (adapter)
        raw_metrics = self.executor.run(
            scenario_type=scenario_type,
            endpoint=endpoint,
            users=users,
            users_min=users_min,
            users_max=users_max,
            ramp_time_seconds=ramp_time_seconds,
            duration_seconds=duration_seconds,
        )

        # Phase 2: Collect metrics via MetricsCollector
        aggregated_metrics = self.metrics_collector.collect(
            request_count=raw_metrics["request_count"],
            error_count=raw_metrics["error_count"],
            latencies=raw_metrics["latencies"],
            duration_seconds=duration_seconds,
        )

        # Phase 3: Compare against baselines via BaselineComparator
        comparator = BaselineComparator(**self.baselines)
        comparison_result = comparator.compare(
            p95_latency_ms=aggregated_metrics["p95_latency_ms"],
            throughput_req_sec=aggregated_metrics["throughput_req_sec"],
            error_rate_percent=aggregated_metrics["error_rate_percent"],
        )

        # Phase 4: Generate HTML report via ReportGenerator
        report_path = self.reporter.generate(
            scenario_type=scenario_type,
            scenario_config={
                "users": users,
                "users_min": users_min,
                "users_max": users_max,
                "ramp_time_seconds": ramp_time_seconds,
                "duration_seconds": duration_seconds,
                "endpoint": endpoint,
            },
            metrics=aggregated_metrics,
            baselines=self.baselines,
            comparison_result=comparison_result,
        )

        # Phase 5: Return structured result
        return LoadTestResult(
            scenario_type=scenario_type,
            p95_latency_ms=aggregated_metrics["p95_latency_ms"],
            p99_latency_ms=aggregated_metrics["p99_latency_ms"],
            throughput_req_sec=aggregated_metrics["throughput_req_sec"],
            error_rate_percent=aggregated_metrics["error_rate_percent"],
            error_count=raw_metrics["error_count"],
            success_count=aggregated_metrics["success_count"],
            request_count=raw_metrics["request_count"],
            comparison_status=comparison_result["status"],
            deviations=comparison_result["deviations"],
            html_report_path=report_path,
            recovery_time_seconds=raw_metrics.get("recovery_time_seconds"),
            memory_growth_percent=raw_metrics.get("memory_growth_percent"),
        )
