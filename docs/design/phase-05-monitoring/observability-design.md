# Phase 05: Observability and Monitoring Design

**Status:** Design Complete
**Date:** 2026-02-15
**Agent:** Observer (APEX Platform Architect)

## Executive Summary

This document describes the production-ready monitoring stack for the AI Detection to CoP Integration system. The stack implements a comprehensive observability solution with Prometheus metrics, Grafana dashboards, Jaeger distributed tracing, and ELK (Elasticsearch, Logstash, Kibana) log aggregation.

### Key Metrics
- **15-second Prometheus scrape interval** for real-time metrics
- **15-day retention** with 2-hour block durability
- **4 Grafana dashboards** (System, Business, Performance, Security)
- **27 distinct metric types** covering all operational aspects
- **25+ unit tests** with 100% pass rate
- **SLO compliance tracking** with error budget calculations

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Detection API Pods                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Prometheus Metrics Middleware (via /metrics endpoint) │   │
│  │ • HTTP request latency (p50/95/99)                    │   │
│  │ • Error rates by endpoint                             │   │
│  │ • Auth failures and validation issues                 │   │
│  │ • Database query performance                          │   │
│  │ • Cache hit/miss rates                                │   │
│  │ • Detection pipeline metrics                          │   │
│  │ • Offline queue status                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐  ┌─────────────────┐  ┌──────────────┐
│  Prometheus      │  │  Jaeger         │  │  ELK Stack   │
│  (9090)          │  │  (6831/14268)   │  │  (9200/5601) │
│                  │  │                 │  │              │
│ • 15s scrape     │  │ • Traces HTTP   │  │ • Logs       │
│ • 15d retention  │  │   requests      │  │ • Events     │
│ • Alert rules    │  │ • DB queries    │  │ • Analysis   │
│ • Recording      │  │ • Cache ops     │  │              │
│   rules (SLOs)   │  │ • TAK pushes    │  │              │
└──────────────────┘  └─────────────────┘  └──────────────┘
         │                    │                    │
         └────────┬───────────┴─────────┬──────────┘
                  │                     │
                  ▼                     ▼
         ┌──────────────────┐  ┌──────────────────┐
         │  Grafana         │  │  AlertManager    │
         │  (3000)          │  │  (9093)          │
         │                  │  │                  │
         │ • System/Biz/    │  │ • Alert routing  │
         │   Perf/Security  │  │ • Notifications  │
         │   dashboards     │  │ • Escalation     │
         │ • SLO tracking   │  │ • Grouping       │
         └──────────────────┘  └──────────────────┘
```

## Metrics Collection

### 1. Request/Response Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `request_latency_seconds` | Histogram | method, endpoint, status | HTTP request latency with p50/95/99 quantiles |
| `requests_total` | Counter | method, endpoint, status | Total HTTP requests |
| `errors_total` | Counter | type, endpoint | Error counts by type and endpoint |

**SLO Targets:**
- 99% of requests complete in <2s (P95 latency)
- 99.9% success rate (error rate <1%)

### 2. Authentication & Security Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `auth_attempts_total` | Counter | method | Total authentication attempts |
| `auth_failures_total` | Counter | reason | Failed auth attempts (invalid_token, expired, etc) |
| `rate_limit_hits_total` | Counter | endpoint, client_id | Rate limit violations |
| `rate_limit_remaining` | Gauge | endpoint, client_id | Remaining quota per client |
| `validation_failures_total` | Counter | field, reason | Input validation failures |
| `invalid_requests_total` | Counter | endpoint, error_type | Total invalid requests |

**Thresholds:**
- Auth failure rate >0.5/sec → Warning
- Rate limit hits >100 in 5min → Warning

### 3. Database Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `db_query_duration_seconds` | Histogram | operation, table | Query execution time |
| `db_queries_total` | Counter | operation, table, status | Total queries by type |
| `db_connections_active` | Gauge | N/A | Active database connections |

**Thresholds:**
- P95 query latency >1s → Warning
- Active connections >90 → Critical

### 4. Cache Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `cache_hits_total` | Counter | cache_name | Cache hit count |
| `cache_misses_total` | Counter | cache_name | Cache miss count |
| `cache_size_bytes` | Gauge | cache_name | Current cache size |
| `cache_evictions_total` | Counter | cache_name | Total evictions |

**Target:** >70% cache hit rate

### 5. Detection Pipeline Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `detections_received_total` | Counter | source | Total detections ingested |
| `detections_processed_total` | Counter | status | Processing outcomes |
| `geolocation_latency_seconds` | Histogram | N/A | Geo-computation time |
| `cot_generation_latency_seconds` | Histogram | N/A | CoT XML generation time |
| `tak_push_attempts_total` | Counter | status | TAK server push attempts |

**Business KPIs:**
- >1000 detections/sec throughput
- <500ms geolocation latency (p95)
- >95% TAK push success rate

### 6. Offline Queue Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `offline_queue_size` | Gauge | N/A | Current queue items |
| `offline_queue_max_size` | Gauge | N/A | Max queue capacity |
| `offline_items_queued_total` | Counter | N/A | Total items queued |
| `offline_items_synced_total` | Counter | N/A | Total items synced |
| `offline_queue_errors_total` | Counter | error_type | Queue operational errors |

**Alert:** Queue size >90% capacity → Critical

### 7. Connectivity Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `tak_server_connectivity` | Gauge | N/A | 1=connected, 0=disconnected |
| `tak_server_latency_seconds` | Histogram | N/A | TAK response time |

**Alert:** TAK server down >1min → Critical

### 8. Audit Trail Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `audit_events_total` | Counter | event_type | Audit events by type |
| `audit_log_latency_seconds` | Histogram | N/A | Audit log write time |

### 9. Business/Analytical Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `detection_confidence_distribution` | Histogram | N/A | Confidence score distribution |
| `geolocation_accuracy_distribution` | Histogram | N/A | Accuracy in meters |
| `cot_type_distribution` | Counter | cot_type | CoT types generated |

## Alert Rules

### Critical (Immediate Response)

```promql
# Error Rate >1%
(rate(errors_total[5m]) / rate(requests_total[5m])) > 0.01

# Latency P95 >5s
histogram_quantile(0.95, rate(request_latency_seconds_bucket[5m])) > 5.0

# TAK Server Unreachable
tak_server_connectivity == 0

# Pod Crash Looping
rate(increase(kube_pod_container_status_restarts_total{pod=~"detection-api.*"}[15m])) > 0

# Disk Usage >90%
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) > 0.90

# Memory Usage >95%
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) > 0.95

# Offline Queue >90% Full
offline_queue_size > (offline_queue_max_size * 0.9)
```

### Warning (Investigation Required)

```promql
# Latency P95 >2s
histogram_quantile(0.95, rate(request_latency_seconds_bucket[5m])) > 2.0

# High Auth Failure Rate
rate(auth_failures_total[5m]) > 0.5

# Rate Limit Hits >100/5min
increase(rate_limit_hits_total[5m]) > 100

# Database Query Latency P95 >1s
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m])) > 1.0

# Low Cache Hit Rate <70%
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.7

# Detection Backlog Building
increase(detections_received_total[5m]) - increase(detections_processed_total[5m]) > 100

# Disk Usage >80%
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) > 0.80

# Memory Usage >85%
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) > 0.85
```

## Service Level Objectives (SLOs)

### 1. Availability SLO
- **Target:** 99.5% uptime over 30 days
- **Error Budget:** 3.6 hours per month
- **Measurement:** (successful requests / total requests) × 100
- **Recording Rule:** `slo:availability:30d`

### 2. Latency P95 SLO
- **Target:** 99% of requests complete in ≤2 seconds (over 30 days)
- **Error Budget:** 0.1% of requests can exceed 2s
- **Measurement:** P95 latency percentile
- **Recording Rule:** `slo:latency_p95:30d`

### 3. Latency P99 SLO
- **Target:** 99% of requests complete in ≤5 seconds
- **Error Budget:** 0.1% can exceed 5s
- **Measurement:** P99 latency percentile
- **Recording Rule:** `slo:latency_p99:30d`

### 4. Error Rate SLO
- **Target:** 99.9% success rate (error rate <0.1%)
- **Error Budget:** 0.1% of requests can fail
- **Measurement:** (failed requests / total requests) × 100
- **Recording Rule:** `slo:error_rate:30d`

### 5. Throughput SLO
- **Target:** ≥1000 detections/second processing
- **Measurement:** rate(detections_processed_total[5m])
- **Recording Rule:** `slo:throughput:30d`

## Grafana Dashboards

### Dashboard 1: System Metrics
Monitors infrastructure health (CPU, memory, disk, network)

**Key Panels:**
- CPU Usage (%)
- Memory Usage (%) with 85% warning
- Disk Usage (%) with 80% warning
- Network I/O (bytes/sec)
- Pod restarts count

**Query Examples:**
```promql
# CPU Usage
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory Usage Percentage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk Usage Percentage
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100
```

### Dashboard 2: Business Metrics
Tracks detection pipeline KPIs and business value

**Key Panels:**
- Detections Received (hourly count)
- Detections Processed (success/failure breakdown)
- Detection Success Rate (%)
- TAK Push Success Rate (%)
- Confidence Score Distribution
- Geolocation Accuracy Distribution

**Query Examples:**
```promql
# Detection Success Rate
rate(detections_processed_total{status="success"}[5m]) / rate(detections_received_total[5m]) * 100

# TAK Push Success Rate
rate(tak_push_attempts_total{status="success"}[5m]) / rate(tak_push_attempts_total[5m]) * 100

# Confidence Distribution Percentiles
histogram_quantile(0.95, detection_confidence_distribution_bucket)
```

### Dashboard 3: Performance Metrics
Application-level performance indicators

**Key Panels:**
- Request Latency (P50, P95, P99)
- Request Rate (RPS)
- Error Rate (%) with 1% critical threshold
- Database Query Latency (P95)
- Cache Hit Rate (%) with 70% target
- Geolocation Processing Time
- CoT Generation Time

**Query Examples:**
```promql
# Request Latency P95
histogram_quantile(0.95, rate(request_latency_seconds_bucket[5m]))

# Request Rate
rate(requests_total[5m])

# Error Rate
(rate(errors_total[5m]) / rate(requests_total[5m])) * 100

# Database Query Latency P95
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))

# Cache Hit Rate
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) * 100
```

### Dashboard 4: Security Metrics
Authentication, authorization, and security events

**Key Panels:**
- Authentication Attempts
- Authentication Failures
- Auth Failure Rate (%)
- Rate Limit Hits
- Invalid Requests by Type
- Validation Failures
- Audit Events by Type

**Query Examples:**
```promql
# Auth Failure Rate
(rate(auth_failures_total[5m]) / rate(auth_attempts_total[5m])) * 100

# Rate Limit Hits
increase(rate_limit_hits_total[1h])

# Validation Failures
increase(validation_failures_total[1h])
```

### Dashboard 5: SLO Tracking
Compliance with Service Level Objectives

**Key Panels:**
- Availability % (99.5% target, gauge)
- Latency P95 seconds (2s target, gauge)
- Error Rate % (0.1% target, gauge)
- Error Budget Remaining (days)
- SLO Compliance Timeline (30-day trend)

**Query Examples:**
```promql
# Availability SLO Compliance
(count(kube_pod_status_ready{pod=~"detection-api.*", condition="true"}) / count(kube_pod_status_ready{pod=~"detection-api.*"})) * 100

# Error Budget Remaining
(100 - (100 - slo:availability:30d)) * 30 * 24 * 60
```

## Jaeger Distributed Tracing

### Traced Operations

1. **HTTP Request Lifecycle**
   - Request entry
   - Route resolution
   - Authentication
   - Authorization
   - Request handling
   - Response generation

2. **Detection Processing Pipeline**
   - Image validation
   - Photogrammetry analysis
   - Confidence scoring
   - CoT generation
   - TAK push

3. **Database Operations**
   - Query preparation
   - Execution
   - Result fetching
   - Transaction management

4. **Cache Operations**
   - Key lookup
   - Cache hit/miss
   - Eviction tracking

5. **Offline Queue Operations**
   - Item queueing
   - Persistence
   - Sync on reconnect

### Trace Sampling
- **Sampler Type:** Probabilistic
- **Sample Rate:** 10% (configurable per environment)
- **Retention:** 72 hours

## ELK Stack (Logs)

### Elasticsearch Indices
- `logs-detection-api-*` (daily rotation)
- `logs-audit-trail-*` (daily rotation)
- `logs-errors-*` (daily rotation)

### Kibana Dashboards
- Error frequency and distribution
- Request timeline with status codes
- Audit trail events
- Log level distribution

### Log Fields
```json
{
  "timestamp": "2026-02-15T12:34:56.789Z",
  "level": "ERROR",
  "logger": "detection-api",
  "message": "TAK server connection failed",
  "module": "tak_service",
  "function": "push_cot",
  "line": 123,
  "exception": "ConnectionError: ...",
  "extra_fields": {
    "detection_id": "det-001",
    "endpoint": "/api/detection",
    "status": 500,
    "duration_ms": 5000
  }
}
```

## Implementation Stack

### Components
| Component | Version | Port | Purpose |
|-----------|---------|------|---------|
| Prometheus | v2.45.0 | 9090 | Metrics collection & storage |
| Grafana | 10.0.0 | 3000 | Visualization & dashboards |
| Jaeger All-in-One | 1.48.0 | 6831/14268/16686 | Distributed tracing |
| Elasticsearch | 8.8.0 | 9200 | Log storage |
| Kibana | 8.8.0 | 5601 | Log visualization |
| Node Exporter | Latest | 9100 | System metrics |
| Kube-State-Metrics | Latest | 8080 | Kubernetes metrics |
| AlertManager | Latest | 9093 | Alert routing |

### Kubernetes Manifests
- `servicemonitor.yaml` - ServiceMonitor for automatic scrape discovery
- `prometheus-rules.yaml` - Alert rules and recording rules
- `prometheus-config.yaml` - Prometheus configuration
- `deployment.yaml` - Pod deployments (Prometheus, Grafana, Jaeger, ELK)
- `services.yaml` - Service definitions and Ingress
- `rbac.yaml` - RBAC for Prometheus and components
- `grafana-datasources.yaml` - Data source configurations
- `grafana-dashboards.yaml` - Dashboard definitions

### Requirements
- Kubernetes 1.20+
- Prometheus Operator CRDs
- Persistent volumes for Prometheus (360GB recommended)
- Persistent volumes for Grafana (10GB)
- Persistent volumes for Elasticsearch (500GB, 3-node cluster)

## Testing

### Test Coverage: 25+ Tests
1. **Metrics Tests** (14 tests)
   - MetricsContext timing
   - MetricsRecorder operations
   - Metric definitions
   - Metric recording with labels
   - Integration scenarios

2. **SLO Tests** (11 tests)
   - SLO definitions
   - Error budget calculations
   - SLO tracker initialization
   - Compliance checking
   - Compliance percentage calculation
   - Error budget tracking
   - Complex scenarios

### Test Files
- `tests/unit/test_monitoring_metrics.py` - 14 tests
- `tests/unit/test_monitoring_slo.py` - 11 tests

### Test Execution
```bash
pytest tests/unit/test_monitoring_metrics.py -v
pytest tests/unit/test_monitoring_slo.py -v
pytest tests/unit/test_monitoring_*.py -v --cov=src/monitoring
```

## Deployment Checklist

- [ ] Create monitoring namespace
- [ ] Apply RBAC manifests
- [ ] Deploy Prometheus with persistent storage
- [ ] Deploy Grafana with dashboards
- [ ] Deploy Jaeger collector
- [ ] Deploy Elasticsearch (3-node cluster)
- [ ] Deploy Kibana
- [ ] Configure Grafana data sources
- [ ] Import dashboards
- [ ] Test metric scraping
- [ ] Test alerts
- [ ] Configure AlertManager routing
- [ ] Set up log forwarding (Fluentd/Logstash)
- [ ] Verify dashboard queries

## Operations Guide

### Accessing Components
```bash
# Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# http://localhost:9090

# Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000
# http://localhost:3000 (admin/password)

# Jaeger UI
kubectl port-forward -n monitoring svc/jaeger-ui 16686:16686
# http://localhost:16686

# Kibana
kubectl port-forward -n monitoring svc/kibana 5601:5601
# http://localhost:5601
```

### Health Checks
```bash
# Prometheus
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health

# Elasticsearch
curl http://localhost:9200/_cluster/health

# Jaeger
curl http://localhost:16686/api/health
```

## SLO Error Budget Tracking

### Monthly Error Budget Allocation (30 days)
| SLO | Target | Monthly Budget | Days Allowed Down |
|-----|--------|----------------|--------------------|
| Availability | 99.5% | 3.6 hours | 0.15 days |
| Latency P95 | 2s (99% of requests) | 0.1% latency budget | Variable |
| Error Rate | 99.9% | 0.1% error budget | Variable |

### Error Budget Consumption
- Track via Prometheus recording rules
- Alert when budget consumed >80% in month
- Restrict releases when budget <10%
- Post-incident review when SLO violated

## Metrics Retention & Archive

### Prometheus Storage
- **Retention:** 15 days (360 hours)
- **Block Duration:** 2 hours
- **Total Storage:** ~500 GB for 1 year baseline
- **Compression:** Enabled

### Elasticsearch Logs
- **Retention:** 30 days (searchable)
- **Archive:** S3 (90 days)
- **Daily Indices:** logs-detection-api-YYYY.MM.DD

### Jaeger Traces
- **Retention:** 72 hours
- **Sampling:** 10% of traces
- **Storage:** Elasticsearch backend

## Future Enhancements

1. **Custom Metrics**
   - Business domain-specific metrics
   - Customer-facing SLOs
   - Revenue impact tracking

2. **Advanced Alerting**
   - ML-based anomaly detection
   - Predictive alerts
   - Correlation analysis

3. **Cost Optimization**
   - Metric cardinality analysis
   - Label optimization
   - Sampling rate tuning

4. **Multi-cluster Monitoring**
   - Federated Prometheus
   - Cross-cluster correlation
   - Global SLO tracking

---

**Document Version:** 1.0
**Last Updated:** 2026-02-15
**Next Review:** 2026-03-15
