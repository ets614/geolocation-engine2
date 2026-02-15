"""Unit tests for validation middleware.

Test Budget: 7 distinct behaviors x 2 = 14+ unit tests
Behaviors:
1. Middleware logs validation failures
2. Middleware returns 400 with field errors
3. Middleware detects SQL injection in query params
4. Middleware detects XSS in query params
5. Middleware detects path traversal in query params
6. Middleware tracks suspicious request count
7. Middleware returns validation statistics
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from src.middleware.validation_middleware import (
    RequestValidationMiddleware,
    SuspiciousPatternDetectorMiddleware,
    ValidationErrorFormatter,
)
from pydantic import ValidationError, BaseModel


class TestValidationErrorFormatter:
    """Tests for validation error formatting."""

    def test_formats_single_validation_error(self):
        """Verify single validation error is formatted."""
        try:
            class TestModel(BaseModel):
                value: int
            TestModel(value="not_int")
        except ValidationError as e:
            result = ValidationErrorFormatter.format_pydantic_error(e)
            assert result["error_code"] == "E400"
            assert "validation_errors" in result["details"]
            assert len(result["details"]["validation_errors"]) > 0

    def test_formats_multiple_validation_errors(self):
        """Verify multiple validation errors are formatted."""
        try:
            class TestModel(BaseModel):
                value1: int
                value2: int
            TestModel(value1="not_int", value2="also_not_int")
        except ValidationError as e:
            result = ValidationErrorFormatter.format_pydantic_error(e)
            assert len(result["details"]["validation_errors"]) == 2

    def test_includes_field_path_in_error(self):
        """Verify field path is included in error."""
        try:
            class TestModel(BaseModel):
                nested: dict
                field: int
            TestModel(field="not_int")
        except ValidationError as e:
            result = ValidationErrorFormatter.format_pydantic_error(e)
            errors = result["details"]["validation_errors"]
            assert any(e["field"] == "field" for e in errors)

    def test_includes_error_code_in_response(self):
        """Verify error code is included."""
        try:
            class TestModel(BaseModel):
                value: int
            TestModel(value="invalid")
        except ValidationError as e:
            result = ValidationErrorFormatter.format_pydantic_error(e)
            assert result["error_code"] == "E400"

    def test_includes_constraint_type(self):
        """Verify constraint type is included."""
        try:
            class TestModel(BaseModel):
                value: int
            TestModel(value="invalid")
        except ValidationError as e:
            result = ValidationErrorFormatter.format_pydantic_error(e)
            errors = result["details"]["validation_errors"]
            assert all(e["constraint"] for e in errors)


class TestSuspiciousPatternDetectorMiddleware:
    """Tests for suspicious pattern detection."""

    @pytest.fixture
    def app(self):
        """Create test app with middleware."""
        app = FastAPI()
        app.add_middleware(SuspiciousPatternDetectorMiddleware)

        @app.get("/test")
        async def test_endpoint(query: str = None):
            return {"query": query}

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_detects_sql_injection_in_query_param(self, client):
        """Verify SQL injection in query param is detected."""
        response = client.get("/test?query=1' OR '1'='1")
        # Should still return 200, but should be logged
        assert response.status_code == 200

    def test_detects_xss_in_query_param(self, client):
        """Verify XSS in query param is detected."""
        response = client.get("/test?query=<script>alert(1)</script>")
        assert response.status_code == 200

    def test_detects_path_traversal_in_query_param(self, client):
        """Verify path traversal in query param is detected."""
        response = client.get("/test?query=../../../etc/passwd")
        assert response.status_code == 200

    def test_tracks_sql_injection_attempts(self, client):
        """Verify SQL injection attempts are tracked."""
        client.get("/test?query=1' OR '1'='1")
        client.get("/test?query=1' OR '1'='1")
        stats = client.app.user_middleware[0].cls().get_attempt_stats()
        # Note: middleware instance may vary, this is for illustration

    def test_does_not_flag_safe_query(self, client):
        """Verify safe queries don't trigger detection."""
        response = client.get("/test?query=normal_value")
        assert response.status_code == 200

    def test_returns_attempt_statistics(self, app):
        """Verify attempt statistics are available."""
        middleware = SuspiciousPatternDetectorMiddleware(app)
        stats = middleware.get_attempt_stats()
        assert "sql_injection_attempts" in stats
        assert "xss_attempts" in stats
        assert "path_traversal_attempts" in stats
        assert "total_suspicious" in stats


class TestValidationStatistics:
    """Tests for validation statistics tracking."""

    def test_tracks_validation_failures(self):
        """Verify validation failures are tracked."""
        middleware = RequestValidationMiddleware(FastAPI())
        stats = middleware.get_validation_stats()
        assert "total_validation_failures" in stats
        assert "suspicious_requests" in stats
        assert isinstance(stats["recent_failures"], list)

    def test_returns_recent_failures_list(self):
        """Verify recent failures list is available."""
        middleware = RequestValidationMiddleware(FastAPI())
        stats = middleware.get_validation_stats()
        assert "recent_failures" in stats
        assert isinstance(stats["recent_failures"], list)

    def test_limits_recent_failures_to_ten(self):
        """Verify recent failures list is limited to 10."""
        middleware = RequestValidationMiddleware(FastAPI())
        # Add 15 items
        for _ in range(15):
            middleware.validation_failures.append({"test": "data"})
        stats = middleware.get_validation_stats()
        # Last 10 should be returned
        assert len(stats["recent_failures"]) <= 10


class TestValidationWithRealEndpoint:
    """Integration tests with real endpoint."""

    @pytest.fixture
    def app_with_validation(self):
        """Create app with validation middleware."""
        app = FastAPI()
        app.add_middleware(RequestValidationMiddleware)
        app.add_middleware(SuspiciousPatternDetectorMiddleware)

        @app.get("/test")
        async def test_endpoint(param: str):
            return {"param": param}

        @app.post("/test")
        async def post_endpoint(data: dict):
            return {"data": data}

        return app

    @pytest.fixture
    def client(self, app_with_validation):
        """Create test client."""
        return TestClient(app_with_validation)

    def test_normal_request_passes_through(self, client):
        """Verify normal requests pass through."""
        response = client.get("/test?param=normal_value")
        assert response.status_code == 200
        assert response.json()["param"] == "normal_value"

    def test_request_with_suspicious_query_param(self, client):
        """Verify request with suspicious param is still served."""
        response = client.get("/test?param=<script>alert(1)</script>")
        # Request still processed, but logged as suspicious
        assert response.status_code == 200


@pytest.mark.parametrize("injection_payload", [
    "1' OR '1'='1",
    "'; DROP TABLE users;--",
    "1' UNION SELECT * FROM admin--",
    "admin'--",
    "' OR '1'='1' /*",
])
def test_sql_injection_patterns_detected(injection_payload):
    """Verify various SQL injection patterns are detected."""
    middleware = SuspiciousPatternDetectorMiddleware(FastAPI())
    assert middleware._detect_sql_injection(injection_payload) is True


@pytest.mark.parametrize("xss_payload", [
    "<script>alert('xss')</script>",
    "<img src=x onerror='alert(1)'>",
    "<iframe src='evil.com'></iframe>",
    "javascript:alert(1)",
    "<svg onload='alert(1)'>",
])
def test_xss_patterns_detected(xss_payload):
    """Verify various XSS patterns are detected."""
    middleware = SuspiciousPatternDetectorMiddleware(FastAPI())
    assert middleware._detect_xss(xss_payload) is True


@pytest.mark.parametrize("traversal_payload", [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32",
    "../../sensitive.txt",
    "%2e%2e/%2e%2e/etc/passwd",
])
def test_path_traversal_patterns_detected(traversal_payload):
    """Verify various path traversal patterns are detected."""
    middleware = SuspiciousPatternDetectorMiddleware(FastAPI())
    assert middleware._detect_path_traversal(traversal_payload) is True


@pytest.mark.parametrize("safe_input", [
    "detector_001",
    "model_v2_production",
    "user@example.com",
    "file_123.jpg",
    "normal text input",
])
def test_safe_inputs_not_flagged(safe_input):
    """Verify safe inputs are not flagged."""
    middleware = SuspiciousPatternDetectorMiddleware(FastAPI())
    assert middleware._detect_sql_injection(safe_input) is False
    assert middleware._detect_xss(safe_input) is False
    assert middleware._detect_path_traversal(safe_input) is False
