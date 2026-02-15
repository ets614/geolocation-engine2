# ADR-001: Select AWS EKS as Cloud Provider

## Status
Accepted

## Date
2026-02-15

## Context
The Detection API requires a production Kubernetes platform. We evaluated AWS EKS, Google GKE, and Azure AKS.

The system processes defense/ISR detection data and pushes Cursor-on-Target (CoT) XML to TAK servers. This workload has elevated security requirements and may need FedRAMP/GovCloud compliance in the future.

## Decision
We selected **AWS EKS** as the cloud provider for Kubernetes infrastructure.

## Rationale

1. **Team capability**: The platform engineering team has primary experience with AWS. Selecting AWS reduces ramp-up time and operational risk.
2. **IAM integration**: AWS IRSA (IAM Roles for Service Accounts) provides pod-level IAM without injecting credentials, which is critical for our least-privilege security model.
3. **Defense alignment**: AWS GovCloud provides a clear path to FedRAMP compliance if the workload moves to classified or government environments.
4. **Ecosystem maturity**: EKS managed add-ons (VPC CNI, CoreDNS, EBS CSI) reduce operational burden. RDS PostgreSQL provides managed HA with automated backups.
5. **Cost parity**: AWS costs are within 10% of GKE and AKS for this workload profile.

## Alternatives Rejected

- **GKE**: Slightly better Kubernetes experience, but limited GovCloud equivalent. Team has less experience.
- **AKS**: Adequate, but weakest managed add-on ecosystem for our use case.

## Consequences

- Infrastructure is written in Terraform with AWS provider
- CI/CD uses OIDC-based AWS authentication (no long-lived credentials)
- Monitoring uses AWS-native CloudWatch for infrastructure, Prometheus for application
- Vendor lock-in mitigated by Terraform modules and Helm charts (portable K8s manifests)
