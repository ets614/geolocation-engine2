"""
BaselineComparator - Validates metrics against SLO baselines (internal service).

Compares performance metrics against established baselines and identifies
regressions (red), improvements (green), and baseline levels (yellow).
"""
from typing import Dict, List, Any


class BaselineComparator:
    """Compares performance metrics against SLO baselines."""

    def __init__(
        self,
        baseline_p95_latency_ms: float = 2000,
        baseline_throughput_req_sec: float = 100,
        baseline_error_rate_percent: float = 0.1,
    ):
        """Initialize with SLO baselines.

        Args:
            baseline_p95_latency_ms: Max acceptable p95 latency (default 2000ms)
            baseline_throughput_req_sec: Min acceptable throughput (default 100 req/sec)
            baseline_error_rate_percent: Max acceptable error rate (default 0.1%)
        """
        self.baseline_p95_latency_ms = baseline_p95_latency_ms
        self.baseline_throughput_req_sec = baseline_throughput_req_sec
        self.baseline_error_rate_percent = baseline_error_rate_percent

    def compare(
        self,
        p95_latency_ms: float,
        throughput_req_sec: float,
        error_rate_percent: float,
    ) -> Dict[str, Any]:
        """Compare metrics against baselines.

        Args:
            p95_latency_ms: Measured p95 latency
            throughput_req_sec: Measured throughput
            error_rate_percent: Measured error rate

        Returns:
            Dict with status ("PASS"/"FAIL") and deviations list
        """
        deviations: List[Dict[str, Any]] = []
        status = "PASS"

        # Check p95 latency
        if p95_latency_ms > self.baseline_p95_latency_ms:
            status = "FAIL"
            percent_change = (
                (p95_latency_ms - self.baseline_p95_latency_ms)
                / self.baseline_p95_latency_ms
                * 100
            )
            deviations.append(
                {
                    "metric": "p95_latency_ms",
                    "baseline": self.baseline_p95_latency_ms,
                    "actual": p95_latency_ms,
                    "percent_change": percent_change,
                    "status": "REGRESSION",
                }
            )
        elif p95_latency_ms < self.baseline_p95_latency_ms * 0.8:
            # Improvement: < 80% of baseline
            percent_change = (
                (p95_latency_ms - self.baseline_p95_latency_ms)
                / self.baseline_p95_latency_ms
                * 100
            )
            deviations.append(
                {
                    "metric": "p95_latency_ms",
                    "baseline": self.baseline_p95_latency_ms,
                    "actual": p95_latency_ms,
                    "percent_change": percent_change,
                    "status": "IMPROVEMENT",
                }
            )

        # Check throughput
        if throughput_req_sec < self.baseline_throughput_req_sec:
            status = "FAIL"
            percent_change = (
                (throughput_req_sec - self.baseline_throughput_req_sec)
                / self.baseline_throughput_req_sec
                * 100
            )
            deviations.append(
                {
                    "metric": "throughput_req_sec",
                    "baseline": self.baseline_throughput_req_sec,
                    "actual": throughput_req_sec,
                    "percent_change": percent_change,
                    "status": "REGRESSION",
                }
            )
        elif throughput_req_sec > self.baseline_throughput_req_sec * 1.2:
            # Improvement: > 120% of baseline
            percent_change = (
                (throughput_req_sec - self.baseline_throughput_req_sec)
                / self.baseline_throughput_req_sec
                * 100
            )
            deviations.append(
                {
                    "metric": "throughput_req_sec",
                    "baseline": self.baseline_throughput_req_sec,
                    "actual": throughput_req_sec,
                    "percent_change": percent_change,
                    "status": "IMPROVEMENT",
                }
            )

        # Check error rate
        if error_rate_percent > self.baseline_error_rate_percent:
            status = "FAIL"
            percent_change = (
                (error_rate_percent - self.baseline_error_rate_percent)
                / self.baseline_error_rate_percent
                * 100
                if self.baseline_error_rate_percent > 0
                else 0
            )
            deviations.append(
                {
                    "metric": "error_rate_percent",
                    "baseline": self.baseline_error_rate_percent,
                    "actual": error_rate_percent,
                    "percent_change": percent_change,
                    "status": "REGRESSION",
                }
            )
        elif error_rate_percent < self.baseline_error_rate_percent * 0.5:
            # Improvement: < 50% of baseline error rate
            percent_change = (
                (error_rate_percent - self.baseline_error_rate_percent)
                / self.baseline_error_rate_percent
                * 100
                if self.baseline_error_rate_percent > 0
                else 0
            )
            deviations.append(
                {
                    "metric": "error_rate_percent",
                    "baseline": self.baseline_error_rate_percent,
                    "actual": error_rate_percent,
                    "percent_change": percent_change,
                    "status": "IMPROVEMENT",
                }
            )

        return {
            "status": status,
            "deviations": deviations,
        }
