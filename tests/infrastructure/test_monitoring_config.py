"""Infrastructure tests for monitoring configuration.

Validates that Prometheus, Grafana, and alert configurations are
structurally correct and aligned with SLO targets.
"""
import json
import os
import pytest
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
INFRA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "infrastructure")
PROMETHEUS_CONFIG = os.path.join(INFRA_DIR, "prometheus", "prometheus.yml")
ALERT_RULES = os.path.join(INFRA_DIR, "prometheus", "alert_rules.yml")
GRAFANA_DASHBOARD = os.path.join(
    INFRA_DIR, "grafana", "dashboards", "detection-api-overview.json"
)
GRAFANA_DATASOURCE = os.path.join(
    INFRA_DIR, "grafana", "provisioning", "datasources", "prometheus.yml"
)


# ---------------------------------------------------------------------------
# Prometheus Configuration Tests
# ---------------------------------------------------------------------------
class TestPrometheusConfig:
    """Validate prometheus.yml structure and settings."""

    @pytest.fixture(autouse=True)
    def load_config(self):
        with open(PROMETHEUS_CONFIG) as f:
            self.config = yaml.safe_load(f)

    def test_global_scrape_interval(self):
        """Scrape interval must be 15s as defined in Helm values."""
        assert self.config["global"]["scrape_interval"] == "15s"

    def test_global_evaluation_interval(self):
        """Evaluation interval must be 30s as defined in Helm values."""
        assert self.config["global"]["evaluation_interval"] == "30s"

    def test_alertmanager_configured(self):
        """Alertmanager target must be defined."""
        alerting = self.config.get("alerting", {})
        assert alerting, "alerting section missing"
        targets = alerting["alertmanagers"][0]["static_configs"][0]["targets"]
        assert len(targets) >= 1

    def test_rule_files_reference(self):
        """Rule files path must be specified."""
        assert len(self.config.get("rule_files", [])) >= 1

    def test_detection_api_scrape_job(self):
        """A scrape job for detection-api must exist."""
        jobs = {j["job_name"] for j in self.config["scrape_configs"]}
        assert "detection-api" in jobs

    def test_detection_api_metrics_path(self):
        """Detection API scrape must use /metrics path."""
        for job in self.config["scrape_configs"]:
            if job["job_name"] == "detection-api":
                assert job.get("metrics_path") == "/metrics"

    def test_detection_api_scrape_interval(self):
        """Detection API specific scrape interval must be 15s."""
        for job in self.config["scrape_configs"]:
            if job["job_name"] == "detection-api":
                assert job.get("scrape_interval") == "15s"


# ---------------------------------------------------------------------------
# Alert Rules Tests
# ---------------------------------------------------------------------------
class TestAlertRules:
    """Validate alert rules are defined for all critical SLO boundaries."""

    @pytest.fixture(autouse=True)
    def load_rules(self):
        with open(ALERT_RULES) as f:
            self.rules_doc = yaml.safe_load(f)
        self.all_alerts = []
        for group in self.rules_doc.get("groups", []):
            for rule in group.get("rules", []):
                if "alert" in rule:
                    self.all_alerts.append(rule)
        self.alert_names = {a["alert"] for a in self.all_alerts}

    def test_has_error_rate_alert(self):
        """Must have an alert for high error rate (SLO: < 0.1%)."""
        assert "HighErrorRate" in self.alert_names

    def test_has_p95_latency_alert(self):
        """Must have an alert for P95 latency (SLO: < 300ms)."""
        assert "HighP95Latency" in self.alert_names

    def test_has_p99_latency_alert(self):
        """Must have an alert for P99 latency (SLO: < 500ms)."""
        assert "HighP99Latency" in self.alert_names

    def test_has_service_down_alert(self):
        """Must have an alert when service instances are down."""
        assert "ServiceDown" in self.alert_names

    def test_has_auth_failure_alert(self):
        """Must have an alert for high authentication failures."""
        assert "HighAuthFailureRate" in self.alert_names

    def test_has_brute_force_alert(self):
        """Must have an alert for potential brute force attacks."""
        assert "AuthBruteForceDetected" in self.alert_names

    def test_has_detection_error_alert(self):
        """Must have an alert for detection processing errors."""
        assert "DetectionProcessingErrors" in self.alert_names

    def test_has_tak_push_failure_alert(self):
        """Must have an alert for TAK push failures."""
        assert "TAKPushFailures" in self.alert_names

    def test_has_queue_alerts(self):
        """Must have alerts for offline queue health."""
        assert "OfflineQueueGrowing" in self.alert_names
        assert "OfflineQueueCritical" in self.alert_names

    def test_has_cache_alert(self):
        """Must have an alert for low cache hit rate."""
        assert "LowCacheHitRate" in self.alert_names

    def test_all_alerts_have_severity(self):
        """Every alert must have a severity label."""
        for alert in self.all_alerts:
            labels = alert.get("labels", {})
            assert "severity" in labels, (
                f"Alert '{alert['alert']}' missing severity label"
            )

    def test_all_alerts_have_summary(self):
        """Every alert must have a summary annotation."""
        for alert in self.all_alerts:
            annotations = alert.get("annotations", {})
            assert "summary" in annotations, (
                f"Alert '{alert['alert']}' missing summary annotation"
            )

    def test_critical_alerts_count(self):
        """Must have at least 3 critical-severity alerts."""
        critical = [
            a for a in self.all_alerts
            if a.get("labels", {}).get("severity") == "critical"
        ]
        assert len(critical) >= 3, f"Only {len(critical)} critical alerts defined"

    def test_error_rate_threshold_matches_slo(self):
        """HighErrorRate threshold must be 0.001 (0.1%)."""
        for alert in self.all_alerts:
            if alert["alert"] == "HighErrorRate":
                assert "0.001" in alert["expr"], (
                    "Error rate threshold does not match 0.1% SLO"
                )

    def test_p95_threshold_matches_slo(self):
        """HighP95Latency threshold must be 0.3 seconds (300ms)."""
        for alert in self.all_alerts:
            if alert["alert"] == "HighP95Latency":
                assert "0.3" in alert["expr"], (
                    "P95 threshold does not match 300ms SLO"
                )

    def test_p99_threshold_matches_slo(self):
        """HighP99Latency threshold must be 0.5 seconds (500ms)."""
        for alert in self.all_alerts:
            if alert["alert"] == "HighP99Latency":
                assert "0.5" in alert["expr"], (
                    "P99 threshold does not match 500ms SLO"
                )


# ---------------------------------------------------------------------------
# Grafana Dashboard Tests
# ---------------------------------------------------------------------------
class TestGrafanaDashboard:
    """Validate Grafana dashboard completeness."""

    @pytest.fixture(autouse=True)
    def load_dashboard(self):
        with open(GRAFANA_DASHBOARD) as f:
            self.dashboard = json.load(f)
        self.panels = [
            p for p in self.dashboard.get("panels", [])
            if p.get("type") != "row"
        ]
        self.panel_titles = {p.get("title", "") for p in self.panels}

    def test_dashboard_has_uid(self):
        """Dashboard must have a stable UID for provisioning."""
        assert self.dashboard.get("uid"), "Dashboard missing uid"

    def test_dashboard_has_title(self):
        """Dashboard must have a descriptive title."""
        assert "Detection API" in self.dashboard.get("title", "")

    def test_auto_refresh_configured(self):
        """Dashboard must have auto-refresh configured."""
        assert self.dashboard.get("refresh"), "Auto-refresh not configured"

    def test_has_slo_panels(self):
        """Must have gauge panels for SLO metrics."""
        slo_keywords = ["Availability", "P95", "P99", "Error Rate"]
        for keyword in slo_keywords:
            matching = [t for t in self.panel_titles if keyword in t]
            assert matching, f"No panel found for SLO metric: {keyword}"

    def test_has_red_metrics_panels(self):
        """Must have panels for Rate, Error, and Duration (RED)."""
        red_keywords = ["Request Rate", "Error Rate", "Latency"]
        for keyword in red_keywords:
            matching = [t for t in self.panel_titles if keyword in t]
            assert matching, f"No panel found for RED metric: {keyword}"

    def test_has_auth_panels(self):
        """Must have panels for authentication metrics."""
        auth_keywords = ["Authentication", "Token"]
        found = any(
            any(kw in t for kw in auth_keywords)
            for t in self.panel_titles
        )
        assert found, "No authentication panels found"

    def test_has_detection_panels(self):
        """Must have panels for detection processing metrics."""
        found = any("Detection" in t for t in self.panel_titles)
        assert found, "No detection processing panels found"

    def test_has_tak_panels(self):
        """Must have panels for TAK server metrics."""
        found = any("TAK" in t for t in self.panel_titles)
        assert found, "No TAK server panels found"

    def test_has_queue_panels(self):
        """Must have panels for offline queue metrics."""
        found = any("Queue" in t for t in self.panel_titles)
        assert found, "No offline queue panels found"

    def test_has_cache_panels(self):
        """Must have panels for cache metrics."""
        found = any("Cache" in t for t in self.panel_titles)
        assert found, "No cache panels found"

    def test_minimum_panel_count(self):
        """Dashboard must have at least 15 data panels."""
        assert len(self.panels) >= 15, (
            f"Only {len(self.panels)} panels -- expected at least 15"
        )

    def test_all_panels_have_datasource(self):
        """Every data panel must reference Prometheus datasource."""
        for panel in self.panels:
            ds = panel.get("datasource")
            assert ds == "Prometheus", (
                f"Panel '{panel.get('title')}' has datasource '{ds}', expected 'Prometheus'"
            )


# ---------------------------------------------------------------------------
# Grafana Datasource Tests
# ---------------------------------------------------------------------------
class TestGrafanaDatasource:
    """Validate Grafana datasource provisioning."""

    @pytest.fixture(autouse=True)
    def load_datasource(self):
        with open(GRAFANA_DATASOURCE) as f:
            self.config = yaml.safe_load(f)

    def test_prometheus_datasource_defined(self):
        """Prometheus must be configured as a datasource."""
        names = [ds["name"] for ds in self.config["datasources"]]
        assert "Prometheus" in names

    def test_prometheus_is_default(self):
        """Prometheus must be the default datasource."""
        for ds in self.config["datasources"]:
            if ds["name"] == "Prometheus":
                assert ds["isDefault"] is True

    def test_prometheus_url(self):
        """Prometheus URL must point to the prometheus service."""
        for ds in self.config["datasources"]:
            if ds["name"] == "Prometheus":
                assert "prometheus" in ds["url"]
