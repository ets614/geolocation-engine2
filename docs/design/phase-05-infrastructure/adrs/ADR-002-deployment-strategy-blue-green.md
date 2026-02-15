# ADR-002: Blue/Green Deployment Strategy

## Status
Accepted

## Date
2026-02-15

## Context
The Detection API has a 99.95% availability SLO and handles TAK/CoT message delivery. Deployment must minimize downtime and provide instant rollback capability.

## Decision
We selected **Blue/Green deployment** with automatic rollback as the primary deployment strategy.

## Rationale

1. **Instant rollback**: Traffic switches via Kubernetes service selector change (< 5 seconds). This is critical for our 21.9-minute monthly error budget.
2. **Zero-downtime deployment**: The new version runs alongside the old version. Traffic is only switched after validation.
3. **Risk profile alignment**: The Detection API processes military ISR detection data. Mixed-version serving (as in rolling updates) risks inconsistent CoT message formats. Blue/Green ensures all traffic hits a single, validated version.
4. **SLO compliance**: With a 99.95% target, we cannot afford extended deployment windows. Blue/Green limits exposure time to the monitoring period (5 minutes).

## Alternatives Rejected

1. **Rolling update**: Rejected because mixed-version pods could produce inconsistent CoT XML during rollout. Also, rollback requires a full reverse rollout (slow).
2. **Canary deployment**: Considered but rejected for MVP. Added complexity (traffic splitting, progressive rollout controller) is not justified for a single-service deployment. Path to canary exists if traffic volume increases.
3. **Recreate**: Rejected because it causes downtime during pod replacement.

## Consequences

- Two deployment slots (blue/green) consume double the compute during deployment
- Service selector toggling requires careful label management
- The deploy.sh script validates rollback capability before every deployment
- CI/CD pipeline includes 5-minute monitoring period before declaring success
