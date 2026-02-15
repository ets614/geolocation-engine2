# Demo Guide

Demonstrations and verification steps for all features delivered in Phases 01-05.

---

## Demo 1: Core Detection Pipeline (Phases 01-03)

### End-to-End Detection Ingestion

```bash
# Start the application
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Submit a detection with full sensor metadata
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "pixel_x": 512,
    "pixel_y": 384,
    "object_class": "vehicle",
    "ai_confidence": 0.92,
    "source": "uav_detection_model_v2",
    "camera_id": "dji_phantom_4",
    "timestamp": "2026-02-15T12:00:00Z",
    "sensor_metadata": {
      "location_lat": 40.7128,
      "location_lon": -74.0060,
      "location_elevation": 100.0,
      "heading": 45.0,
      "pitch": -30.0,
      "roll": 0.0,
      "focal_length": 3000.0,
      "sensor_width_mm": 6.4,
      "sensor_height_mm": 4.8,
      "image_width": 1920,
      "image_height": 1440
    }
  }'
```

**Expected:** 201 Created with CoT XML containing geolocation coordinates, GREEN confidence flag, and TAK-compatible format.

### Verify Pipeline Steps

```bash
# Health check (always available)
curl http://localhost:8000/api/v1/health
# Expected: {"status": "running", "version": "0.1.0", "service": "Detection to COP"}
```

---

## Demo 2: Authentication (Phase 04)

### JWT Token Flow

```bash
# Generate a JWT token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id": "demo-client", "client_secret": "demo-secret"}'
# Save the access_token and refresh_token from the response

# Use the token for authenticated requests
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{ ... detection payload ... }'

# Refresh an expired token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

### API Key Flow

```bash
# Create an API key (requires admin auth)
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "uav-feed-1", "scopes": ["write:detections"]}'
# Save the returned API key (shown only once)

# Use the API key
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -H "X-API-Key: geoeng_dev_abc123..." \
  -d '{ ... detection payload ... }'
```

### Verify Authentication Blocks Unauthorized Access

```bash
# No auth header -> 401 Unauthorized
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -d '{ ... }'
# Expected: 401

# Invalid token -> 401 Unauthorized
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Authorization: Bearer invalid-token" \
  -H "Content-Type: application/json" \
  -d '{ ... }'
# Expected: 401
```

---

## Demo 3: Rate Limiting (Phase 04)

```bash
# Send rapid requests to trigger rate limiting
for i in $(seq 1 15); do
  echo "Request $i:"
  curl -s -o /dev/null -w "HTTP %{http_code}" \
    http://localhost:8000/api/v1/health
  echo ""
done
# Unauthenticated limit: 10 requests per bucket
# After 10 requests, expect HTTP 429 with Retry-After header

# Check rate limit headers on any response
curl -v http://localhost:8000/api/v1/health 2>&1 | grep X-RateLimit
# X-RateLimit-Limit: 10
# X-RateLimit-Remaining: 9
# X-RateLimit-Reset: <seconds>
```

---

## Demo 4: Input Sanitization (Phase 04)

```bash
# SQL injection attempt -> rejected
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"object_class": "vehicle; DROP TABLE detections;--", ...}'
# Expected: 400 Bad Request (sanitization failure)

# XSS attempt -> rejected
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"source": "<script>alert(1)</script>", ...}'
# Expected: 400 Bad Request (sanitization failure)

# Path traversal attempt -> rejected
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"camera_id": "../../../etc/passwd", ...}'
# Expected: 400 Bad Request (sanitization failure)
```

---

## Demo 5: Monitoring and Metrics (Phase 04-05)

### Prometheus Metrics

```bash
# View raw metrics
curl http://localhost:8000/metrics

# Key metrics to look for:
# http_requests_total{method="POST",endpoint="/api/v1/detections",status_code="201"}
# http_request_duration_seconds_bucket{...}
# auth_attempts_total{result="success"}
# detections_processed_total{status="success",confidence_flag="GREEN"}
# tak_push_total{status="success"}
# offline_queue_size
# cache_hits_total
```

### Grafana Dashboards

```bash
# Start monitoring stack
docker compose -f infrastructure/docker-compose.monitoring.yml up -d

# Open Grafana
open http://localhost:3000
# Login: admin / admin

# Navigate to: Dashboards -> Detection API Overview
# Panels show:
#   - Request rate (requests/sec)
#   - Error rate (%)
#   - P95 latency (ms)
#   - Detection confidence distribution (GREEN/YELLOW/RED)
#   - TAK push success/failure rate
#   - Offline queue depth
#   - Cache hit rate
```

### Alert Rules

```bash
# View alert rules in Prometheus
open http://localhost:9090/alerts

# 19 alert rules across 7 groups:
# - SLO: error rate, P95, P99
# - Availability: service down, low instances
# - Authentication: failure rate, brute force
# - Detection: processing errors, slow processing
# - TAK Server: push failures, latency
# - Offline Queue: growing, critical, stale
# - Cache: low hit rate
```

---

## Demo 6: Load Testing (Phase 04)

```bash
# Quick load test (50 concurrent users, 2 minutes)
locust -f tests/load/locustfile.py \
  --host http://localhost:8000 \
  --headless -u 50 -r 10 --run-time 2m

# Full load test with HTML report
./tests/load/run_load_test.sh http://localhost:8000 200 20 5m

# View results:
# - Total requests processed
# - Requests per second
# - P50/P95/P99 latency
# - Error rate
# - SLO compliance (< 0.1% errors, < 300ms P95)
```

### Load Test User Profiles

| Profile | Behavior | Weight |
|---------|----------|--------|
| DetectionSubmitter | POST /api/v1/detections continuously | 60% |
| AuditReader | GET /api/v1/health + read endpoints | 30% |
| AdminUser | POST /api/v1/auth/token + key management | 10% |

---

## Demo 7: Security Headers (Phase 04)

```bash
# Check security headers on any response
curl -v http://localhost:8000/api/v1/health 2>&1 | grep -E "^< "

# Expected headers:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Content-Security-Policy: default-src 'none'
# Cache-Control: no-store
# X-Request-ID: <uuid>
```

---

## Demo 8: Full Test Suite (All Phases)

```bash
# Run complete test suite
pytest tests/ -v --tb=short

# Expected: 331+ tests passing, 0 failures
# Coverage: ~93.5%

# Run with coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Open coverage report
open htmlcov/index.html
```

---

## Demo 9: Kubernetes Deployment (Phase 05)

```bash
# Deploy with Helm
helm install detection-api kubernetes/helm-charts/ \
  --namespace detection-system \
  --create-namespace

# Verify pods
kubectl get pods -n detection-system
# Expected: 3 pods Running (blue-green with 3 replicas)

# Check HPA
kubectl get hpa -n detection-system
# Expected: HPA targeting 70% CPU, 75% memory

# Verify network policies
kubectl get networkpolicy -n detection-system
# Expected: default-deny-all, allow-dns-egress, allow-ingress, allow-tak-egress

# Check PDB
kubectl get pdb -n detection-system
# Expected: minAvailable=2

# Port-forward and test
kubectl port-forward svc/detection-api-service -n detection-system 8000:8000
curl http://localhost:8000/api/v1/health
```

---

## Demo 10: Disaster Recovery (Phase 05)

### Simulate Blue-Green Deployment

```bash
# Current state: traffic on green
kubectl get svc detection-api-service -n detection-system -o jsonpath='{.spec.selector.slot}'
# Expected: green

# Switch to blue (simulate rollback)
kubectl patch svc detection-api-service -n detection-system \
  -p '{"spec":{"selector":{"slot":"blue"}}}'

# Verify traffic switched
kubectl get endpoints detection-api-service -n detection-system

# Switch back to green
kubectl patch svc detection-api-service -n detection-system \
  -p '{"spec":{"selector":{"slot":"green"}}}'
```

### Verify Backup

```bash
# Check backup CronJob
kubectl get cronjob -n detection-system
# Expected: detection-db-backup, schedule "0 2 * * *"

# Trigger manual backup
kubectl create job --from=cronjob/detection-db-backup manual-backup -n detection-system

# Verify backup completed
kubectl get jobs -n detection-system
kubectl logs job/manual-backup -n detection-system
```

---

## Performance Benchmarks

| Metric | Measured | Target | Status |
|--------|----------|--------|--------|
| Geolocation calculation | ~3ms | < 10ms | PASS |
| CoT XML generation | ~1ms | < 5ms | PASS |
| E2E detection ingestion | ~15ms | < 100ms | PASS |
| P95 latency (100 req/s) | ~45ms | < 300ms | PASS |
| P99 latency (100 req/s) | ~120ms | < 500ms | PASS |
| Sustained throughput | 150+ req/s | 100 req/s | PASS |
| Error rate (sustained load) | < 0.05% | < 0.1% | PASS |
| Cache hit rate (reads) | ~75% | > 60% | PASS |
