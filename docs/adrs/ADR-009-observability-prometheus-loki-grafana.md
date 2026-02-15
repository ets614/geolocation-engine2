# ADR-009: Observability Stack -- Prometheus, Loki, Grafana

## Status: Accepted

## Date: 2026-02-15

## Context

The detection-api currently outputs structured JSON logs to stdout and has Prometheus scrape annotations on pods, but no observability infrastructure is deployed. The Phase 04 CI/CD pipeline includes Slack notifications for deployment success/failure, but there is no runtime monitoring, alerting, or log aggregation.

Production operation of a tactical detection system requires:
- Real-time visibility into detection pipeline health (throughput, latency, error rate)
- TAK integration monitoring (push success/failure rate, queue depth)
- Alerting on anomalies before operators notice degradation
- Log aggregation for post-incident investigation (correlated by detection_id)
- Audit trail query capability beyond direct SQLite access

## Decision

Deploy the Prometheus + Loki + Grafana (PLG) stack for observability.

**Components**:
- **Prometheus**: Scrapes `/metrics` endpoint from detection-api pods. Stores time-series metrics (15-day retention).
- **Promtail**: DaemonSet that ships pod stdout/stderr logs to Loki.
- **Loki**: Stores and indexes logs by labels (app, namespace, pod). Lightweight, label-based indexing.
- **Grafana**: Unified dashboard for metrics (Prometheus datasource) and logs (Loki datasource). Built-in alerting replaces standalone Alertmanager for MVP.

**Application Integration**: The crafter adds a `/metrics` endpoint to FastAPI using `prometheus-fastapi-instrumentator` or equivalent library. Custom metrics (queue depth, confidence flag distribution, TAK push counters) exposed via Prometheus client library.

## Alternatives Considered

### ELK Stack (Elasticsearch + Logstash + Kibana)
- **Pros**: Powerful full-text search, mature ecosystem, rich Kibana visualizations
- **Cons**: Elasticsearch requires 2-4GB memory per node minimum, complex cluster management (shards, replicas, index lifecycle), significant operational overhead
- **Rejection reason**: Resource requirements disproportionate for single-service deployment. A 3-node Elasticsearch cluster would consume more resources than the application itself. Loki achieves 90% of the log query capability at 10% of the resource cost.

### Cloud-Native Observability (CloudWatch/Stackdriver/Azure Monitor)
- **Pros**: Zero infrastructure management, auto-scaling, deep cloud integration
- **Cons**: Vendor lock-in, requires cloud connectivity, per-GB pricing at scale
- **Rejection reason**: Tactical/military deployments may operate in air-gapped environments without cloud connectivity. Open source stack runs entirely on-premise.

### Datadog / New Relic (SaaS)
- **Pros**: Best-in-class UX, APM, infrastructure monitoring, log management in one platform
- **Cons**: Proprietary, per-host pricing ($15-23/host/month for infrastructure, additional for APM/logs)
- **Rejection reason**: Proprietary tool not acceptable per open-source-first principle. Cost scales with infrastructure. Not available in air-gapped environments.

### Prometheus + Alertmanager (no Loki/Grafana for logs)
- **Pros**: Simpler, metrics-only
- **Cons**: No log aggregation, operators must `kubectl logs` for debugging
- **Rejection reason**: Post-incident investigation requires correlated log queries by detection_id across pod restarts. `kubectl logs` only shows current pod logs and is lost on pod termination.

## Consequences

### Positive
- Unified observability: metrics + logs + alerts in single Grafana interface
- Lightweight: Loki indexes labels not content, 10x less storage than Elasticsearch
- Existing JSON logging works without application changes (Promtail scrapes stdout)
- Existing Prometheus annotations on pods work without changes
- Cost: $0 (all AGPL/Apache licensed, self-hosted)
- Air-gap compatible: entire stack runs on-premise
- Detection pipeline visibility: throughput, latency, error rate, confidence distribution
- TAK integration visibility: push success rate, queue depth trends

### Negative
- AGPL license on Grafana/Loki: modifications must be open-sourced (not a concern for internal deployment, only if distributing modified version)
- Additional infrastructure pods (Prometheus, Loki, Promtail, Grafana) consume cluster resources (~2GB total memory)
- Grafana dashboards require initial configuration (provisioned via JSON, one-time setup)
- Log retention limited by Loki storage (14-day default, configurable)
- No full-text search: Loki queries use LogQL with label filtering, not Elasticsearch-style full-text search

### Resource Budget

| Component | CPU Request | Memory Request | Storage |
|-----------|------------|----------------|---------|
| Prometheus | 250m | 512Mi | 10Gi PVC |
| Loki | 250m | 256Mi | 20Gi PVC |
| Promtail (per node) | 100m | 128Mi | - |
| Grafana | 100m | 256Mi | 1Gi PVC |
| **Total** | ~700m | ~1.2Gi | ~31Gi |

### Deployment
- Installed via Helm charts: `kube-prometheus-stack` for Prometheus, `loki-stack` for Loki+Promtail, `grafana` chart
- All deployed to `monitoring` namespace
- NetworkPolicy allows Prometheus to scrape `detection-system` namespace pods
- Grafana provisioned with detection pipeline dashboards via ConfigMap
