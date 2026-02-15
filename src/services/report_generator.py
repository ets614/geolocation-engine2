"""
ReportGenerator - Creates HTML baseline comparison reports (internal service).

Generates HTML reports with:
  - Scenario configuration summary
  - Performance metrics table
  - Baseline comparison (red/yellow/green indicators)
  - Deviation details
"""
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class ReportGenerator:
    """Generates HTML load test reports with baseline comparison."""

    def __init__(self, output_dir: str = "/tmp/load_test_reports"):
        """Initialize report generator.

        Args:
            output_dir: Directory to write HTML reports to
        """
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        scenario_type: str,
        scenario_config: Dict[str, Any],
        metrics: Dict[str, Any],
        baselines: Dict[str, Any],
        comparison_result: Dict[str, Any],
    ) -> str:
        """Generate HTML report with baseline comparison.

        Args:
            scenario_type: "ramp_up", "sustained", "spike", or "soak"
            scenario_config: Test configuration (users, duration, etc.)
            metrics: Collected performance metrics
            baselines: SLO baseline thresholds
            comparison_result: Baseline comparison result

        Returns:
            Path to generated HTML report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"load_test_{scenario_type}_{timestamp}.html"
        report_path = os.path.join(self.output_dir, report_filename)

        # Build HTML content
        html_content = self._build_html(
            scenario_type=scenario_type,
            scenario_config=scenario_config,
            metrics=metrics,
            baselines=baselines,
            comparison_result=comparison_result,
        )

        # Write to file
        with open(report_path, "w") as f:
            f.write(html_content)

        return report_path

    def _build_html(
        self,
        scenario_type: str,
        scenario_config: Dict[str, Any],
        metrics: Dict[str, Any],
        baselines: Dict[str, Any],
        comparison_result: Dict[str, Any],
    ) -> str:
        """Build HTML report content.

        Returns:
            HTML content as string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = comparison_result.get("status", "UNKNOWN")
        status_color = "green" if status == "PASS" else "red"

        # Build metrics table rows
        metrics_rows = self._build_metrics_rows(metrics, baselines, comparison_result)

        # Build deviations section
        deviations_section = self._build_deviations_section(
            comparison_result.get("deviations", [])
        )

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Load Test Report - {scenario_type}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #333;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .status-{status.lower()} {{
            background-color: {status_color};
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            font-weight: bold;
            display: inline-block;
            margin-bottom: 10px;
        }}
        .config-section {{
            background-color: white;
            padding: 15px;
            margin-bottom: 20px;
            border-left: 4px solid #0066cc;
            border-radius: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            margin-bottom: 20px;
            border-radius: 5px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background-color: #0066cc;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f9f9f9;
        }}
        .metric-pass {{
            background-color: #e6ffe6;
        }}
        .metric-fail {{
            background-color: #ffe6e6;
        }}
        .metric-improvement {{
            color: green;
            font-weight: bold;
        }}
        .metric-regression {{
            color: red;
            font-weight: bold;
        }}
        .baseline {{
            color: orange;
            font-weight: bold;
        }}
        .deviations-section {{
            background-color: white;
            padding: 15px;
            margin-top: 20px;
            border-left: 4px solid #ff6600;
            border-radius: 5px;
        }}
        .deviation-item {{
            padding: 10px;
            margin: 5px 0;
            border-left: 3px solid #ff6600;
            background-color: #fff5e6;
        }}
        h1 {{
            margin: 0 0 10px 0;
        }}
        h2 {{
            color: #333;
            border-bottom: 2px solid #0066cc;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        .timestamp {{
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Load Test Report - {scenario_type.upper()}</h1>
        <div class="timestamp">Generated: {timestamp}</div>
        <div class="status-{status.lower()}">Status: {status}</div>
    </div>

    <div class="config-section">
        <h2>Test Configuration</h2>
        <table>
            <tr>
                <td><strong>Scenario Type</strong></td>
                <td>{scenario_type}</td>
            </tr>
            {self._build_config_rows(scenario_config)}
        </table>
    </div>

    <h2>Performance Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Baseline</th>
            <th>Actual</th>
            <th>Status</th>
            <th>Change</th>
        </tr>
        {metrics_rows}
    </table>

    {deviations_section}

    <div style="margin-top: 40px; padding: 20px; background-color: white; border-radius: 5px;">
        <p style="color: #666; font-size: 12px;">
            Load test framework v1.0 | Powered by Locust
        </p>
    </div>
</body>
</html>
"""
        return html

    def _build_config_rows(self, config: Dict[str, Any]) -> str:
        """Build HTML table rows for test configuration."""
        rows = []
        for key, value in config.items():
            if value is not None:
                display_key = key.replace("_", " ").title()
                rows.append(f"<tr><td><strong>{display_key}</strong></td><td>{value}</td></tr>")
        return "\n".join(rows)

    def _build_metrics_rows(
        self, metrics: Dict[str, Any], baselines: Dict[str, Any],
        comparison_result: Dict[str, Any]
    ) -> str:
        """Build HTML table rows for metrics vs baselines."""
        rows = []
        deviations_by_metric = {d["metric"]: d for d in comparison_result.get("deviations", [])}

        # P95 Latency
        if "p95_latency_ms" in metrics:
            baseline_val = baselines.get("p95_latency_ms", "N/A")
            actual_val = metrics["p95_latency_ms"]
            deviation = deviations_by_metric.get("p95_latency_ms")
            status_class = self._get_status_class(deviation)
            change_text = ""
            if deviation:
                change_text = f'{deviation["percent_change"]:.1f}% ({deviation["status"]})'
            rows.append(
                f'<tr class="{status_class}"><td><strong>P95 Latency (ms)</strong></td>'
                f'<td class="baseline">{baseline_val}</td>'
                f'<td>{actual_val:.0f}</td>'
                f'<td>{status_class.replace("metric-", "").upper()}</td>'
                f'<td>{change_text}</td></tr>'
            )

        # P99 Latency
        if "p99_latency_ms" in metrics:
            actual_val = metrics["p99_latency_ms"]
            rows.append(
                f'<tr><td><strong>P99 Latency (ms)</strong></td>'
                f'<td>-</td>'
                f'<td>{actual_val:.0f}</td>'
                f'<td>-</td>'
                f'<td>-</td></tr>'
            )

        # Throughput
        if "throughput_req_sec" in metrics:
            baseline_val = baselines.get("throughput_req_sec", "N/A")
            actual_val = metrics["throughput_req_sec"]
            deviation = deviations_by_metric.get("throughput_req_sec")
            status_class = self._get_status_class(deviation)
            change_text = ""
            if deviation:
                change_text = f'{deviation["percent_change"]:.1f}% ({deviation["status"]})'
            rows.append(
                f'<tr class="{status_class}"><td><strong>Throughput (req/sec)</strong></td>'
                f'<td class="baseline">{baseline_val}</td>'
                f'<td>{actual_val:.1f}</td>'
                f'<td>{status_class.replace("metric-", "").upper()}</td>'
                f'<td>{change_text}</td></tr>'
            )

        # Error Rate
        if "error_rate_percent" in metrics:
            baseline_val = baselines.get("error_rate_percent", "N/A")
            actual_val = metrics["error_rate_percent"]
            deviation = deviations_by_metric.get("error_rate_percent")
            status_class = self._get_status_class(deviation)
            change_text = ""
            if deviation:
                change_text = f'{deviation["percent_change"]:.1f}% ({deviation["status"]})'
            rows.append(
                f'<tr class="{status_class}"><td><strong>Error Rate (%)</strong></td>'
                f'<td class="baseline">{baseline_val}</td>'
                f'<td>{actual_val:.2f}</td>'
                f'<td>{status_class.replace("metric-", "").upper()}</td>'
                f'<td>{change_text}</td></tr>'
            )

        return "\n".join(rows)

    def _get_status_class(self, deviation: Optional[Dict[str, Any]]) -> str:
        """Get CSS class for metric status."""
        if not deviation:
            return "metric-pass"
        status = deviation.get("status", "")
        if status == "REGRESSION":
            return "metric-fail"
        elif status == "IMPROVEMENT":
            return "metric-pass"
        return "metric-pass"

    def _build_deviations_section(self, deviations: list) -> str:
        """Build HTML section for deviations (regressions/improvements)."""
        if not deviations:
            return '<div class="deviations-section"><p>No deviations from baseline.</p></div>'

        deviation_items = []
        for dev in deviations:
            metric = dev.get("metric", "Unknown")
            status = dev.get("status", "Unknown")
            percent_change = dev.get("percent_change", 0)
            baseline = dev.get("baseline", "N/A")
            actual = dev.get("actual", "N/A")

            color = "red" if status == "REGRESSION" else "green"
            deviation_items.append(
                f'<div class="deviation-item" style="border-color: {color}">'
                f'<strong style="color: {color}">{status}</strong>: '
                f'{metric} - {percent_change:.1f}% change '
                f'(baseline: {baseline:.2f}, actual: {actual:.2f})'
                f'</div>'
            )

        return (
            f'<div class="deviations-section"><h2>Baseline Deviations</h2>'
            f'{"".join(deviation_items)}</div>'
        )
