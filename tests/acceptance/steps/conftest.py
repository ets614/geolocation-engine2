"""
Pytest-BDD Configuration and Fixtures
AI Detection to COP Translation System - Acceptance Tests

This conftest provides:
- Test container management (REST API service, TAK simulator, database)
- HTTP client for API testing
- Database fixtures and utilities
- Service health check utilities
- Common test data and constants
"""

import pytest
import requests
import json
import time
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import sqlite3
import uuid


# ============================================================================
# TEST CONSTANTS AND CONFIGURATION
# ============================================================================

TEST_CONFIG = {
    "api_host": "localhost",
    "api_port": int(os.getenv("TEST_API_PORT", "8000")),
    "tak_simulator_host": "localhost",
    "tak_simulator_port": int(os.getenv("TEST_TAK_PORT", "9000")),
    "database_url": os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:"),
    "api_timeout_seconds": 10,
    "health_check_retries": 30,
    "health_check_delay_ms": 200,
}

# Geolocation thresholds
GEOLOCATION_THRESHOLDS = {
    "accuracy_threshold_m": 500,
    "confidence_minimum": 0.6,
    "max_accuracy_yellow": 1000,
}

# Sample detection templates
SAMPLE_FIRE_DETECTION = {
    "source": "satellite_fire_api",
    "latitude": 32.1234,
    "longitude": -117.5678,
    "confidence": 85,  # 0-100 scale
    "type": "fire",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "accuracy_meters": 200,
    "metadata": {
        "sensor": "LANDSAT-8",
        "band": "thermal"
    }
}

SAMPLE_UAV_DETECTION = {
    "source": "uav_1",
    "lat": 32.1234,
    "lon": -117.5678,
    "conf": 0.92,  # 0-1 scale
    "type": "vehicle",
    "ts": datetime.now(timezone.utc).isoformat(),
    "accuracy_meters": 25,
    "metadata": {
        "sensor": "onboard_ai",
        "model": "YOLOv5"
    }
}


# ============================================================================
# CONTEXT/REQUEST FIXTURE - Holds test state
# ============================================================================

@pytest.fixture
def context():
    """
    Test context object that maintains state across steps.

    Used to pass data between When/Then steps in the same scenario.
    """
    class Context:
        def __init__(self):
            self.http_responses = {}  # Dict of response_id -> response object
            self.last_response = None
            self.last_response_body = None
            self.detection_ids = []  # Track created detection IDs
            self.queued_detections = []
            self.synced_detections = []
            self.errors = []
            self.detections = {}  # Dict of detection_id -> detection data
            self.geolocation_flags = {}  # Dict of detection_id -> flag (GREEN/YELLOW/RED)
            self.api_latencies = []  # Track latencies for performance validation
            self.audit_trail = []  # Track audit events
            self.timestamp_start = datetime.now(timezone.utc)

        def reset(self):
            """Reset context for new scenario"""
            self.__dict__.clear()
            self.__dict__.update(self.__init__.__code__.co_consts[1].__dict__)

    return Context()


@pytest.fixture
def http_client():
    """HTTP client for API testing with timeout and retry logic"""
    class HTTPClient:
        def __init__(self, base_url: str, timeout: int = 10):
            self.base_url = base_url
            self.timeout = timeout
            self.session = requests.Session()

        def post(self, endpoint: str, json_data: Dict[str, Any], **kwargs) -> requests.Response:
            """POST request with error handling"""
            url = f"{self.base_url}{endpoint}"
            try:
                response = self.session.post(
                    url,
                    json=json_data,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                # Return response even on error for assertion testing
                if hasattr(e, 'response'):
                    return e.response
                raise

        def get(self, endpoint: str, **kwargs) -> requests.Response:
            """GET request with error handling"""
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            return response

        def put(self, endpoint: str, json_data: Dict[str, Any], **kwargs) -> requests.Response:
            """PUT request with error handling"""
            url = f"{self.base_url}{endpoint}"
            response = self.session.put(url, json=json_data, timeout=self.timeout, **kwargs)
            return response

        def close(self):
            """Close session"""
            self.session.close()

    base_url = f"http://{TEST_CONFIG['api_host']}:{TEST_CONFIG['api_port']}"
    client = HTTPClient(base_url, timeout=TEST_CONFIG['api_timeout_seconds'])
    yield client
    client.close()


# ============================================================================
# SERVICE FIXTURES - Start/stop services for testing
# ============================================================================

@pytest.fixture(scope="session")
def api_service():
    """
    Start the detection ingestion service.

    In real implementation, this would start the FastAPI service.
    For now, assumes service is running on configured host:port.
    """
    # Verify service is running with health check
    max_retries = TEST_CONFIG['health_check_retries']
    retry_delay = TEST_CONFIG['health_check_delay_ms'] / 1000.0

    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"http://{TEST_CONFIG['api_host']}:{TEST_CONFIG['api_port']}/api/v1/health",
                timeout=5
            )
            if response.status_code == 200:
                print(f"API service ready after {attempt * retry_delay:.1f}s")
                yield
                return
        except requests.exceptions.RequestException:
            pass

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    raise RuntimeError(
        f"API service did not become ready at "
        f"{TEST_CONFIG['api_host']}:{TEST_CONFIG['api_port']} "
        f"after {max_retries * retry_delay:.1f}s"
    )


@pytest.fixture(scope="session")
def tak_simulator():
    """
    TAK Server simulator for testing output integration.

    Simulates TAK Server GeoJSON subscription endpoint.
    In real setup, would use testcontainers.
    """
    # Verify TAK simulator is running
    max_retries = TEST_CONFIG['health_check_retries']
    retry_delay = TEST_CONFIG['health_check_delay_ms'] / 1000.0

    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"http://{TEST_CONFIG['tak_simulator_host']}:{TEST_CONFIG['tak_simulator_port']}/health",
                timeout=5
            )
            if response.status_code == 200:
                print(f"TAK simulator ready after {attempt * retry_delay:.1f}s")
                yield
                return
        except requests.exceptions.RequestException:
            pass

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    raise RuntimeError(
        f"TAK simulator did not become ready at "
        f"{TEST_CONFIG['tak_simulator_host']}:{TEST_CONFIG['tak_simulator_port']}"
    )


@pytest.fixture
def database():
    """
    SQLite database fixture for acceptance tests.

    Provides clean database for each test scenario.
    """
    # Create temporary database file
    temp_db = tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False)
    db_path = temp_db.name
    temp_db.close()

    # Initialize schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables (simplified schema for testing)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            confidence REAL NOT NULL,
            accuracy_flag TEXT NOT NULL,
            sync_status TEXT DEFAULT 'PENDING_SYNC',
            received_at TEXT NOT NULL,
            processed_at TEXT,
            operator_verified BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS offline_queue (
            id TEXT PRIMARY KEY,
            detection_json TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING_SYNC',
            created_at TEXT NOT NULL,
            synced_at TEXT,
            retry_count INTEGER DEFAULT 0,
            error_message TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_trail (
            id TEXT PRIMARY KEY,
            detection_id TEXT,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT,
            status TEXT DEFAULT 'success'
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def iso_timestamp():
    """Generate ISO format timestamp for consistent test data"""
    def _timestamp(delta_seconds=0):
        dt = datetime.now(timezone.utc)
        if delta_seconds:
            from datetime import timedelta
            dt = dt + timedelta(seconds=delta_seconds)
        return dt.isoformat()
    return _timestamp


@pytest.fixture
def generate_detection_id():
    """Generate unique detection IDs"""
    def _generate():
        return f"det-{uuid.uuid4().hex[:12]}"
    return _generate


@pytest.fixture
def sample_detections():
    """Provide sample detection data for tests"""
    return {
        "fire": SAMPLE_FIRE_DETECTION.copy(),
        "uav": SAMPLE_UAV_DETECTION.copy(),
        "camera": {
            "source": "camera_47",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "confidence": 0.78,
            "type": "person",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "accuracy_meters": 10,
        }
    }


# ============================================================================
# AUTOUSE FIXTURES - Run for every test
# ============================================================================

@pytest.fixture(autouse=True)
def reset_context(context):
    """Reset context before each scenario"""
    context.reset()


@pytest.fixture(autouse=True)
def services(api_service, tak_simulator):
    """Ensure services are running"""
    pass


# ============================================================================
# ASSERTION HELPERS
# ============================================================================

def assert_status_code(response: requests.Response, expected_code: int, message: str = ""):
    """Assert HTTP status code"""
    assert response.status_code == expected_code, (
        f"Expected status {expected_code}, got {response.status_code}. "
        f"Response: {response.text}. {message}"
    )


def assert_json_valid(response: requests.Response) -> Dict:
    """Assert response is valid JSON and return parsed body"""
    try:
        return response.json()
    except json.JSONDecodeError as e:
        raise AssertionError(f"Response is not valid JSON: {response.text}") from e


def assert_has_field(obj: Dict, field: str, message: str = ""):
    """Assert object has field"""
    assert field in obj, f"Expected field '{field}' in response. {message}"


def assert_field_equals(obj: Dict, field: str, expected_value, message: str = ""):
    """Assert field has expected value"""
    assert_has_field(obj, field, message)
    actual = obj[field]
    assert actual == expected_value, (
        f"Expected {field}={expected_value}, got {actual}. {message}"
    )


# ============================================================================
# PYTEST HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "walking_skeleton: Walking skeleton test")
    config.addinivalue_line("markers", "milestone_1: First milestone feature")
    config.addinivalue_line("markers", "smoke_test: Smoke test")
    config.addinivalue_line("markers", "happy_path: Happy path scenario")
    config.addinivalue_line("markers", "error_handling: Error handling scenario")
    config.addinivalue_line("markers", "boundary: Boundary condition test")
    config.addinivalue_line("markers", "performance: Performance test")
    config.addinivalue_line("markers", "sla: SLA validation test")
    config.addinivalue_line("markers", "slow: Slow test")
    config.addinivalue_line("markers", "skip: Skip test")
    config.addinivalue_line("markers", "infrastructure: Infrastructure test")
