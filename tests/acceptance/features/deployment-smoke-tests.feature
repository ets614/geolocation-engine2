@infrastructure @deployment
Feature: Deployment and Infrastructure Validation
  As a DevOps engineer
  I want to validate system deployment and infrastructure readiness
  So that the system is ready for production operations

  Background:
    Given the deployment environment is prepared
    And monitoring and alerting are configured
    And database migrations have been applied

  @smoke_test @deployment
  Scenario: System health checks validate all components ready
    Given the system is freshly deployed
    When the health check endpoint is called at GET /api/v1/health
    Then response status is 200 OK
    And response includes overall status: UP
    And response includes component health status:
      | component           | status | expected_detail           |
      | api_server          | UP     | listening on port 8000    |
      | database            | UP     | connection pool 5/10      |
      | tak_server          | UP     | ping successful           |
      | offline_queue       | UP     | 0 queued                  |
      | geolocation_service | UP     | model loaded              |
      | audit_trail_service | UP     | logging operational       |
    And health check completes in <1 second
    And JSON response is valid and parseable

  @deployment @configuration
  Scenario: Database schema is initialized and ready
    Given fresh PostgreSQL/SQLite database
    When system starts and applies migrations
    Then all required tables are created:
      | table_name          | purpose                        |
      | detections          | Store detection records        |
      | offline_queue       | Local queue for offline mode   |
      | audit_trail         | Immutable event log            |
      | detection_sources   | Configuration of API sources   |
    And all tables have required indexes:
      | table          | index_columns           | purpose              |
      | detections     | detection_id            | Primary lookup       |
      | detections     | source, timestamp       | Query by source/time |
      | offline_queue  | status, created_at      | Queue management     |
      | audit_trail    | detection_id, event_at  | Audit searching      |
    And schema version is recorded
    And schema is compatible with application code

  @deployment @docker
  Scenario: Docker container starts and becomes healthy
    Given Docker image is built successfully
    When Docker container is started with:
      | environment_variable | value                  |
      | DATABASE_URL         | sqlite:///data/app.db  |
      | TAK_SERVER_URL       | http://tak-sim:9000    |
      | LOG_LEVEL            | INFO                   |
      | PORT                 | 8000                   |
    Then container starts within 10 seconds
    And application process is running (not crashed)
    And port 8000 is listening and accepting connections
    And health check endpoint responds with UP
    And startup logs show: "Application ready at http://0.0.0.0:8000"

  @deployment @configuration
  Scenario: Configuration is loaded from environment variables
    Given environment variables are set:
      | variable_name        | value                          |
      | DATABASE_URL         | sqlite:///./data/test.db       |
      | TAK_SERVER_URL       | https://tak-server.example.com |
      | SATELLITE_API_KEY    | test-key-abc-123               |
      | LOG_LEVEL            | DEBUG                          |
      | API_KEY_VALIDATION   | true                           |
    When system starts
    Then configuration is loaded from environment:
      | setting              | loaded_value                   |
      | database.url         | sqlite:///./data/test.db       |
      | tak_server.url       | https://tak-server.example.com |
      | api_keys.satellite   | test-key-abc-123 (masked in logs) |
      | logging.level        | DEBUG                          |
      | api.key_validation   | true                           |
    And sensitive values are not logged in plaintext
    And configuration is validated on startup
    And invalid configuration fails fast with clear error

  @deployment @api_documentation
  Scenario: API documentation is available and correct
    Given the system is running
    When I access GET /api/docs
    Then response status is 200 OK
    And OpenAPI/Swagger documentation is returned
    And documentation includes all endpoints:
      | endpoint                 | method | description              |
      | /api/v1/detections       | POST   | Ingest detection         |
      | /api/v1/detections/{id}  | GET    | Get detection status     |
      | /api/v1/health           | GET    | System health check      |
      | /api/v1/audit/{det_id}   | GET    | Audit trail              |
    And documentation includes request/response schemas
    And documentation includes error code definitions
    And documentation is usable in Swagger UI or similar

  @deployment @monitoring
  Scenario: Prometheus metrics endpoint is available
    Given the system is running
    When I access GET /metrics
    Then response status is 200 OK
    And response includes Prometheus-formatted metrics
    And metrics include:
      | metric_name                      | type      | example_value |
      | detection_ingestion_total        | counter   | 1250          |
      | detection_validation_latency_ms  | histogram | p95=45        |
      | tak_output_latency_ms            | histogram | p95=800       |
      | offline_queue_depth              | gauge     | 0             |
      | system_reliability_percent       | gauge     | 99.8          |
    And metrics can be scraped by Prometheus
    And metrics data is valid and recent

  @deployment @logging
  Scenario: Application logging is configured correctly
    Given the system is running with LOG_LEVEL=INFO
    When detections are processed
    Then logs are written in JSON format:
      | log_field      | example_value            |
      | timestamp      | 2026-02-17T14:35:42Z     |
      | level          | INFO / WARN / ERROR      |
      | logger         | detection_service        |
      | event          | detection_received       |
      | detection_id   | det-12345-abc            |
      | source         | satellite_fire_api       |
    And logs are structured for easy parsing
    And logs can be exported to log aggregation system
    And sensitive data (API keys) is not logged
    And logs are rotated/managed to prevent filling disk

  @deployment @security
  Scenario: API requires authentication for protected endpoints
    Given the system is running
    When I call POST /api/v1/detections without authentication
    Then response status is 401 Unauthorized
    And error message indicates: "API key required"
    When I call POST /api/v1/detections with invalid API key
    Then response status is 401 Unauthorized
    And error message indicates: "Invalid API key"
    When I call POST /api/v1/detections with valid API key
    Then response status is 202 Accepted
    And detection is processed normally

  @deployment @backup
  Scenario: Database backup and recovery procedures work
    Given system is running with SQLite database
    When database is backed up
    Then backup file includes:
      | content              | status      |
      | detections table     | backed up   |
      | offline_queue table  | backed up   |
      | audit_trail table    | backed up   |
      | metadata             | backed up   |
    And backup is consistent and not corrupted
    When backup is restored to new database
    Then all data is recovered:
      | metric               | verification |
      | detection count      | matches original |
      | queue contents       | identical    |
      | audit trail events   | complete     |
    And system operates normally with recovered data

  @deployment @kubernetes
  Scenario: Kubernetes manifests deploy system successfully
    Given Kubernetes manifests are prepared:
      | resource_type | name                        |
      | Deployment    | detection-cop-translator    |
      | Service       | detection-cop-api           |
      | ConfigMap     | app-config                  |
      | Secret        | api-keys                    |
    When manifests are applied to cluster: kubectl apply -f
    Then resources are created successfully:
      | resource_type | status  | details              |
      | Deployment    | Running | 1 replica ready      |
      | Service       | Active  | ClusterIP assigned   |
      | ConfigMap     | Active  | 4 keys loaded        |
      | Secret        | Active  | 3 secrets loaded     |
    And pod is healthy: (Ready 1/1)
    And API endpoint is accessible
    And health check responds with UP

  @deployment @startup_latency
  Scenario: System startup time is acceptable
    Given system is stopped
    When system is started
    Then startup timeline:
      | milestone               | max_time | actual_time |
      | Process starts          | 2s       | 0.5s        |
      | Database connects       | 5s       | 1.2s        |
      | Migrations applied      | 10s      | 2.3s        |
      | Services initialized    | 15s      | 3.1s        |
      | Health check passes     | 20s      | 4.5s        |
      | Ready to serve requests | 20s      | 4.5s        |
    And system is ready for requests in <20 seconds

  @deployment @data_migration
  Scenario: Existing data is preserved during deployment upgrade
    Given existing database with 1000 detections
    When system is upgraded from v1.0 to v1.1
    And database migration is applied
    Then all 1000 detections are preserved:
      | check                   | status  |
      | No data loss            | ✓       |
      | No corruption           | ✓       |
      | Audit trail maintained  | ✓       |
      | Queue status preserved  | ✓       |
    And system operates normally with migrated data

  @deployment @integration
  Scenario: Integrated deployment with TAK Server simulator works
    Given Docker Compose stack with:
      | service              | status  |
      | app                  | Running |
      | tak-simulator        | Running |
      | postgres/sqlite      | Running |
    When I POST a detection to app:8000/api/v1/detections
    Then detection flows through complete pipeline:
      | step       | status  |
      | Ingest     | ✓       |
      | Validate   | ✓       |
      | Transform  | ✓       |
      | Output     | ✓       |
      | TAK Receive| ✓       |
    And detection appears on TAK simulator map
    And end-to-end latency is <2 seconds
    And audit trail is complete
    And system is production-ready

  @deployment @rollback
  Scenario: Deployment rollback works if needed
    Given current production version v1.0
    And new version v1.1 has critical issue
    When rollback to v1.0 is triggered
    Then previous version is restored:
      | component        | status  |
      | Application code | v1.0    |
      | Database schema  | v1.0    |
      | Configuration    | v1.0    |
      | Data             | intact  |
    And system operates normally at v1.0
    And no data loss occurs
    And rollback completes within 5 minutes

  @monitoring @alerting
  Scenario: Critical alerts are configured and tested
    Given monitoring system is configured
    When critical conditions occur:
      | condition                   | threshold | trigger   |
      | API error rate              | >1%       | 5/5 met   |
      | TAK output latency          | >5s       | 3/5 met   |
      | Database connection pool    | 100% used | 1/1 met   |
      | Offline queue depth         | >1000     | triggered |
      | Detection validation failure| >5%       | 2/5 met   |
    Then alerts are triggered:
      | alert_id | severity | notification_sent |
      | api_errors_high | critical | ✓ |
      | tak_latency_high | warning | ✓ |
      | db_pool_exhausted | critical | ✓ |
      | queue_depth_high | warning | ✓ |
      | validation_errors_high | warning | ✓ |
    And alerts are sent to configured channels (PagerDuty, Slack, email)
    And alert details are sufficient for diagnosis

  @deployment @ci_cd
  Scenario: CI/CD pipeline validates deployment
    Given code is committed to main branch
    When CI/CD pipeline runs:
      | stage              | checks                    |
      | Build              | Docker image builds       |
      | Unit tests         | >80% coverage             |
      | Integration tests  | All acceptance tests pass |
      | Security scan      | No high-severity issues   |
      | Performance test   | Latency <2s, p99 <5s     |
      | Deploy to staging  | Deployment successful     |
      | Smoke tests        | Health checks pass        |
    Then pipeline reports success
    And all gates are passed
    And deployment to production is approved
    And release notes are auto-generated
