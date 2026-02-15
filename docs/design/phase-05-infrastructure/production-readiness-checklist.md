# Production Readiness Checklist - Detection API

## Infrastructure

- [x] VPC with public/private/database subnet tiers
- [x] NAT gateways per AZ for HA (production)
- [x] VPC flow logs enabled
- [x] EKS cluster with private endpoint (production)
- [x] Separate node groups: application and monitoring
- [x] Auto-scaling configured (3-10 application nodes)
- [x] EBS CSI driver for persistent volumes
- [x] gp3 storage class for performance

## Security

- [x] KMS encryption for EKS secrets
- [x] KMS encryption for RDS storage
- [x] KMS encryption for S3 backups
- [x] IRSA for pod-level IAM (no shared credentials)
- [x] Network policies (default deny, explicit allow)
- [x] Pod security context (non-root, dropped capabilities, seccomp)
- [x] RDS SSL enforced (rds.force_ssl = 1)
- [x] RBAC with least-privilege roles
- [x] tfsec + checkov in CI pipeline
- [x] Trivy container image scanning
- [x] Secrets via Kubernetes Secrets (path to External Secrets Operator)

## Deployment

- [x] Blue/Green deployment strategy
- [x] Rollback validated before every deployment
- [x] Helm charts with templated manifests
- [x] Health checks: liveness, readiness, startup probes
- [x] PodDisruptionBudget (minAvailable: 2)
- [x] Graceful shutdown (preStop hook, terminationGracePeriod)
- [x] Pod anti-affinity (spread across nodes)
- [x] Resource requests and limits defined
- [x] Deployment script with auto-rollback option

## Observability

- [x] Prometheus Operator with ServiceMonitor
- [x] Grafana dashboard: SLO, RED metrics, business metrics
- [x] Loki for log aggregation with structured JSON parsing
- [x] Alertmanager with severity-based routing
- [x] SLO-based alerting (error budget burn rate)
- [x] Business logic alerts (queue size, TAK health, accuracy)
- [x] Infrastructure alerts (CPU, memory, disk, pod health)
- [x] CloudWatch for EKS control plane and VPC flow logs

## Database

- [x] RDS PostgreSQL 16 with Multi-AZ
- [x] Read replica for query offloading
- [x] Automated backups (30-day retention)
- [x] Performance Insights enabled
- [x] Enhanced Monitoring enabled
- [x] Custom parameter group (tuned for workload)
- [x] Connection pooling ready (max_connections: 200)
- [x] CloudWatch alarms (CPU, storage, replica lag)
- [x] IAM database authentication enabled

## Disaster Recovery

- [x] Database backup script (PostgreSQL + SQLite queue)
- [x] S3 backup storage with encryption and lifecycle policies
- [x] Disaster recovery script with RTO tracking
- [x] RTO target: < 30 minutes
- [x] RPO target: < 1 hour
- [x] Cross-region replication ready (S3 module supports it)

## CI/CD

- [x] Application pipeline: lint, test, build, scan, deploy, validate
- [x] Infrastructure pipeline: validate, security scan, plan, apply
- [x] OIDC-based AWS authentication (no long-lived credentials)
- [x] Environment-specific deployment gates
- [x] Production requires manual approval
- [x] Terraform state in S3 with DynamoDB locking

## Documentation

- [x] Infrastructure architecture document
- [x] ADR: Cloud provider selection (AWS EKS)
- [x] ADR: Deployment strategy (Blue/Green)
- [x] ADR: Observability stack (Prometheus/Grafana/Loki)
- [x] Cost estimates per environment
- [x] Runbook references in alert annotations
