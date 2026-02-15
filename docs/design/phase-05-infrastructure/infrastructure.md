# Infrastructure Design - Detection API

## Overview

Production infrastructure for the AI Detection to COP Integration Service on AWS EKS.

## Architecture

```
                       ┌──────────────────────────────────────────────────────┐
                       │                     AWS Region (us-east-1)           │
                       │                                                      │
    Internet ──────────┤  ┌──────────────────────────────────────────┐        │
                       │  │           VPC (10.0.0.0/16)              │        │
                       │  │                                          │        │
                       │  │  ┌─────────────────────────────────┐     │        │
                       │  │  │  Public Subnets (3 AZs)         │     │        │
                       │  │  │  - ALB/NLB                      │     │        │
                       │  │  │  - NAT Gateways (3x HA)         │     │        │
                       │  │  └───────────┬─────────────────────┘     │        │
                       │  │              │                           │        │
                       │  │  ┌───────────▼─────────────────────┐     │        │
                       │  │  │  Private Subnets (3 AZs)        │     │        │
                       │  │  │                                 │     │        │
                       │  │  │  ┌─────────────────────────┐    │     │        │
                       │  │  │  │  EKS Cluster (v1.29)    │    │     │        │
                       │  │  │  │                         │    │     │        │
                       │  │  │  │  App Nodes (3-10):      │    │     │        │
                       │  │  │  │   detection-api (3)     │    │     │        │
                       │  │  │  │   blue/green deploy     │    │     │        │
                       │  │  │  │                         │    │     │        │
                       │  │  │  │  Mon Nodes (2-3):       │    │     │        │
                       │  │  │  │   prometheus (2)        │    │     │        │
                       │  │  │  │   grafana (1)           │    │     │        │
                       │  │  │  │   loki (1)              │    │     │        │
                       │  │  │  └─────────────────────────┘    │     │        │
                       │  │  └───────────┬─────────────────────┘     │        │
                       │  │              │                           │        │
                       │  │  ┌───────────▼─────────────────────┐     │        │
                       │  │  │  Database Subnets (3 AZs)       │     │        │
                       │  │  │  - RDS PostgreSQL 16 (Multi-AZ) │     │        │
                       │  │  │  - Read Replica                 │     │        │
                       │  │  │  - No internet access           │     │        │
                       │  │  └─────────────────────────────────┘     │        │
                       │  └──────────────────────────────────────────┘        │
                       │                                                      │
                       │  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │
                       │  │ S3       │  │ KMS      │  │ CloudWatch   │       │
                       │  │ Backups  │  │ Encrypt  │  │ Logs/Metrics │       │
                       │  └──────────┘  └──────────┘  └──────────────┘       │
                       └──────────────────────────────────────────────────────┘
```

## Cloud Provider Selection

**AWS EKS** selected over GKE and AKS. Rationale:

| Criterion              | AWS EKS    | GKE        | AKS        |
|------------------------|------------|------------|------------|
| IAM Integration        | Excellent  | Good       | Good       |
| Gov/Defense Compliance | GovCloud   | Limited    | Gov regions|
| Team Experience        | Primary    | Secondary  | Limited    |
| Managed Add-ons        | Rich       | Rich       | Moderate   |
| Cost (estimated)       | ~$1,200/mo | ~$1,100/mo | ~$1,150/mo |

## SLO Definitions

| SLO            | Target  | Measurement                        | Error Budget (30d) |
|----------------|---------|------------------------------------|--------------------|
| Availability   | 99.95%  | Successful HTTP responses / total  | 21.9 minutes       |
| Latency (p99)  | < 500ms | 99th percentile response time      | --                 |
| Latency (p95)  | < 300ms | 95th percentile response time      | --                 |
| Data Freshness | < 60s   | Detection-to-CoT pipeline latency  | --                 |

## Environment Comparison

| Resource            | Dev          | Staging       | Production     |
|---------------------|--------------|---------------|----------------|
| NAT Gateways        | 1 (single)   | 1 (single)    | 3 (per-AZ HA)  |
| EKS App Nodes       | 1-4 t3.large | 2-6 m6i.large | 3-10 m6i.xlarge|
| EKS Mon Nodes       | 1-2 t3.med   | 1-2 t3.large  | 2-3 m6i.large  |
| RDS Instance         | t3.medium    | r6g.medium    | r6g.large      |
| RDS Multi-AZ         | No           | Yes           | Yes            |
| RDS Read Replica     | No           | No            | Yes            |
| Backup Retention     | 7 days       | 14 days       | 30 days        |
| S3 Backup Retention  | 30 days      | 90 days       | 365 days       |
| VPC Flow Logs        | 30 days      | 60 days       | 90 days        |
| Est. Monthly Cost    | ~$350        | ~$650         | ~$1,200        |

## Security Controls

1. **Encryption at rest**: KMS for EKS secrets, RDS, S3
2. **Encryption in transit**: TLS everywhere, forced SSL on RDS
3. **Network isolation**: Private subnets, network policies, security groups
4. **IAM**: IRSA for pod-level permissions, least-privilege roles
5. **Secrets**: External Secrets Operator or Sealed Secrets (not in-cluster plaintext)
6. **Scanning**: tfsec + checkov in CI, Trivy for container images
7. **Audit**: VPC flow logs, EKS control plane logs, CloudTrail

## Deployment Strategy

Blue/Green with automatic rollback:

```
1. Deploy to inactive slot (green)
2. Run smoke tests on green
3. Switch service selector to green
4. Monitor for 5 minutes
5. If OK: decommission blue
6. If FAIL: switch back to blue (automatic)
```

Rollback procedure is validated BEFORE every deployment proceeds.

## Disaster Recovery

| Metric | Target | Mechanism                     |
|--------|--------|-------------------------------|
| RTO    | < 30m  | Automated restore scripts     |
| RPO    | < 1h   | Hourly RDS snapshots + S3     |

Recovery tested via `scripts/backup/disaster-recovery.sh`.
