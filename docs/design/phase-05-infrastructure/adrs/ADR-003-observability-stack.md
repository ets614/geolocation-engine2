# ADR-003: Prometheus + Grafana + Loki Observability Stack

## Status
Accepted

## Date
2026-02-15

## Context
The Detection API requires metrics, logging, and alerting to maintain SLOs and provide operational visibility. We need to select an observability stack.

## Decision
We selected the **Prometheus Operator + Grafana + Loki** stack deployed within the EKS cluster.

## Rationale

1. **SLO-native**: Prometheus recording rules and alert rules directly express SLO burn rates. Error budget alerts drive operational response.
2. **Kubernetes-native**: The Prometheus Operator (ServiceMonitor CRDs) integrates with Kubernetes service discovery. No configuration drift.
3. **Cost**: Self-hosted stack eliminates per-metric or per-log-line charges from SaaS providers. Estimated savings of $500-800/month versus Datadog at our projected volume.
4. **Team familiarity**: The team has existing Prometheus/Grafana experience.
5. **Loki for logs**: Loki provides log aggregation with label-based querying, consistent with Prometheus's label model. Lower resource consumption than Elasticsearch.

## Alternatives Rejected

1. **Datadog**: Excellent UX, but per-host and per-metric pricing is expensive for a project of this scale. Also, defense-adjacent data should remain in our controlled environment.
2. **AWS CloudWatch + X-Ray**: Good AWS integration, but limited PromQL expressiveness for SLO burn-rate calculations. Used as supplementary infrastructure monitoring, not primary.
3. **Elastic Stack (EFK)**: Higher resource consumption than Loki. Over-engineered for our log volume.

## Consequences

- Prometheus and Grafana require dedicated monitoring nodes (2-3 m6i.large instances)
- Alerting rules are version-controlled in `kubernetes/monitoring/prometheus/alerting-rules.yaml`
- Grafana dashboards are provisioned via ConfigMaps (GitOps-friendly)
- Loki retention is 30 days; older logs archived to S3 via lifecycle policy
