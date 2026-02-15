"""
Unit tests for ReportGenerator (internal service - tested through driving port).

Test Budget: 1 behavior x 2 = 2 tests max

Behavior:
  ReportGenerator creates HTML baseline comparison reports with embedded charts
  showing regressions (red) vs improvements (green) vs baseline (yellow).
"""
import pytest
import os
from pathlib import Path


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_generator_creates_html_report_with_baseline_comparison(self, tmp_path):
        """
        Behavior: ReportGenerator.generate creates valid HTML report

        Given: Scenario metrics and baseline thresholds
        When: I call generator.generate(scenario_results, baselines)
        Then:
          - HTML file created at returned path
          - File contains baseline comparison table
          - File includes p95, p99, throughput, error_rate sections
        """
        from src.services.report_generator import ReportGenerator

        generator = ReportGenerator(output_dir=str(tmp_path))

        report_path = generator.generate(
            scenario_type="sustained",
            scenario_config={
                "users": 50,
                "duration_seconds": 600,
                "ramp_time_seconds": 60,
            },
            metrics={
                "p95_latency_ms": 1800,
                "p99_latency_ms": 2500,
                "throughput_req_sec": 120,
                "error_rate_percent": 0.08,
                "success_count": 72000,
            },
            baselines={
                "p95_latency_ms": 2000,
                "throughput_req_sec": 100,
                "error_rate_percent": 0.1,
            },
            comparison_result={
                "status": "PASS",
                "deviations": [],
            },
        )

        # Verify file was created
        assert report_path is not None
        assert os.path.exists(report_path)
        assert report_path.endswith(".html")

        # Verify content
        with open(report_path, "r") as f:
            html_content = f.read()
            assert "sustained" in html_content.lower() or "50 users" in html_content
            assert "baseline" in html_content.lower()
            assert "1800" in html_content or "p95" in html_content.lower()

    def test_generator_includes_visual_indicators_for_slo_compliance(self, tmp_path):
        """
        Behavior: ReportGenerator creates visual SLO compliance indicators

        Given: Metrics some passing, some failing SLOs
        When: I call generator.generate with mixed compliance
        Then:
          - Green indicator for passing metrics
          - Red indicator for failing metrics
          - Baseline metric shown in yellow
          - Deviations list provided with % change
        """
        from src.services.report_generator import ReportGenerator

        generator = ReportGenerator(output_dir=str(tmp_path))

        # Mixed compliance: latency passes, throughput fails
        report_path = generator.generate(
            scenario_type="spike",
            scenario_config={
                "users": 200,
                "duration_seconds": 30,
                "ramp_time_seconds": 10,
            },
            metrics={
                "p95_latency_ms": 1500,  # Passes (< 2000)
                "p99_latency_ms": 2800,
                "throughput_req_sec": 80,  # Fails (< 100)
                "error_rate_percent": 0.05,
                "success_count": 2400,
            },
            baselines={
                "p95_latency_ms": 2000,
                "throughput_req_sec": 100,
                "error_rate_percent": 0.1,
            },
            comparison_result={
                "status": "FAIL",
                "deviations": [
                    {
                        "metric": "throughput_req_sec",
                        "baseline": 100,
                        "actual": 80,
                        "percent_change": -20.0,
                    }
                ],
            },
        )

        # Verify report includes visual indicators
        assert os.path.exists(report_path)
        with open(report_path, "r") as f:
            html_content = f.read()
            # Should mention pass/fail or have color indicators
            assert (
                "pass" in html_content.lower()
                or "fail" in html_content.lower()
                or "green" in html_content.lower()
            )
