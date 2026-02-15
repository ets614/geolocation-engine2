# Monitoring & Observability Setup Guide

## Architecture

```
Detection API (:8000/metrics) --> Prometheus (:9090) --> Grafana (:3000)
                                       |
                                  Alert Rules --> Alertmanager (:9093)
```

## Quick Start (Local Development)

```bash
# Start monitoring stack
docker compose -f infrastructure/docker-compose.monitoring.yml up -d

# Start Detection API
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000 (admin/admin)
```

## Metrics Exposed

### RED Metrics (Request Rate / Errors / Duration)
| Metric | Type | Labels |
|--------|------|--------|
| `http_requests_total` | Counter | method, endpoint, status_code |
| `http_request_duration_seconds` | Histogram | method, endpoint |
| `http_requests_in_progress` | Gauge | method, endpoint |

### Authentication
| Metric | Type | Labels |
|--------|------|--------|
| `auth_attempts_total` | Counter | result (success/failure/expired) |
| `auth_token_generation_total` | Counter | client_id |

### Detection Processing
| Metric | Type | Labels |
|--------|------|--------|
| `detections_processed_total` | Counter | status, confidence_flag |
| `detection_processing_duration_seconds` | Histogram | - |
| `detection_geolocation_confidence` | Histogram | - |

### TAK Server
| Metric | Type | Labels |
|--------|------|--------|
| `tak_push_total` | Counter | status (success/failure/queued) |
| `tak_push_duration_seconds` | Histogram | - |

### Offline Queue
| Metric | Type | Labels |
|--------|------|--------|
| `offline_queue_size` | Gauge | - |
| `offline_queue_oldest_item_age_seconds` | Gauge | - |

### Cache
| Metric | Type | Labels |
|--------|------|--------|
| `cache_hits_total` | Counter | cache_name |
| `cache_misses_total` | Counter | cache_name |

## SLO Targets

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Error rate | < 0.1% | > 0.1% for 2m |
| P95 latency | < 300ms | > 300ms for 5m |
| P99 latency | < 500ms | > 500ms for 5m |
| Availability | > 99.9% | Instance down > 1m |

## Alert Rules

19 alert rules across 7 groups:
- **SLO alerts**: Error rate, P95/P99 latency
- **Availability**: Service down, too few instances, no requests
- **Authentication**: High failure rate, brute force detection
- **Detection processing**: Error rate, slow processing, low confidence
- **TAK server**: Push failures, push latency
- **Offline queue**: Growing, critical, stale items
- **Cache**: Low hit rate

## Load Testing

```bash
# Quick local test
locust -f tests/load/locustfile.py --host http://localhost:8000 \
  --headless -u 50 -r 10 --run-time 2m

# Full test with report
./tests/load/run_load_test.sh http://localhost:8000 200 20 5m
```

## Kubernetes Deployment

Pods already have Prometheus annotations configured:
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

Network policy `allow-prometheus-scrape` permits scraping from the monitoring namespace.

## File Structure

```
infrastructure/
  prometheus/
    prometheus.yml          # Scrape configuration
    alert_rules.yml         # 19 alert rules in 7 groups
  grafana/
    dashboards/
      detection-api-overview.json  # Operational dashboard
    provisioning/
      datasources/prometheus.yml   # Auto-provision Prometheus
      dashboards/dashboards.yml    # Auto-load dashboards
  docker-compose.monitoring.yml    # Local monitoring stack
tests/
  load/
    locustfile.py           # 3 user types, SLO compliance report
    run_load_test.sh        # Runner script with defaults
  infrastructure/
    test_monitoring_config.py   # 38 config validation tests
    test_metrics_endpoint.py    # 13 /metrics endpoint tests
```
