"""
MetricsCollector - Aggregates performance metrics (internal service).

Calculates percentiles (p50, p95, p99), throughput, and error rate
from raw latency and request data.
"""
from typing import List, Dict, Any
from statistics import median, quantiles


class MetricsCollector:
    """Collects and aggregates performance metrics."""

    def collect(
        self,
        request_count: int,
        error_count: int,
        latencies: List[float],
        duration_seconds: float,
    ) -> Dict[str, Any]:
        """Aggregate performance metrics from raw data.

        Args:
            request_count: Total number of requests
            error_count: Number of failed requests
            latencies: List of response latencies in milliseconds
            duration_seconds: Test duration in seconds

        Returns:
            Dict with p50, p95, p99 latencies, throughput, error_rate, etc.
        """
        # Sort latencies for percentile calculation
        sorted_latencies = sorted(latencies)

        # Calculate latency percentiles
        p50 = self._percentile(sorted_latencies, 50)
        p95 = self._percentile(sorted_latencies, 95)
        p99 = self._percentile(sorted_latencies, 99)
        p999 = self._percentile(sorted_latencies, 99.9)

        # Calculate throughput (req/sec)
        throughput = request_count / duration_seconds if duration_seconds > 0 else 0

        # Calculate error rate
        error_rate = (error_count / request_count * 100) if request_count > 0 else 0

        # Calculate success count
        success_count = request_count - error_count

        # Calculate average latency
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        # Calculate min/max
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        return {
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
            "p999_latency_ms": p999,
            "avg_latency_ms": avg_latency,
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "throughput_req_sec": throughput,
            "error_rate_percent": error_rate,
            "error_count": error_count,
            "success_count": success_count,
            "request_count": request_count,
            "total_requests": request_count,
            "duration_seconds": duration_seconds,
        }

    def _percentile(self, sorted_data: List[float], percent: float) -> float:
        """Calculate percentile from sorted data.

        Args:
            sorted_data: Sorted list of values
            percent: Percentile to calculate (0-100)

        Returns:
            Value at specified percentile
        """
        if not sorted_data:
            return 0.0

        index = (percent / 100) * (len(sorted_data) - 1)
        lower = int(index)
        upper = lower + 1

        if upper >= len(sorted_data):
            return float(sorted_data[-1])

        # Linear interpolation between lower and upper values
        lower_value = sorted_data[lower]
        upper_value = sorted_data[upper]
        fraction = index - lower

        return lower_value + fraction * (upper_value - lower_value)
