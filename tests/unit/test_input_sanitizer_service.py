"""Unit tests for input validation and sanitization service.

Test Budget: 5 distinct behaviors x 2 = 10 unit tests max
Behaviors:
1. Sanitize strings (HTML escape, length check)
2. Detect SQL injection patterns
3. Detect XSS patterns
4. Detect path traversal attacks
5. Sanitize dictionaries recursively
"""
import pytest

from src.services.input_sanitizer_service import (
    InputSanitizerService,
    InputSanitizationError,
)


class TestStringSanitization:
    """Test string sanitization through the service port."""

    def test_sanitize_escapes_html_special_chars(self):
        """Service escapes HTML special characters."""
        service = InputSanitizerService()
        result = service.sanitize_string('<b>bold</b> & "quoted"')

        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result
        assert "&quot;" in result

    def test_sanitize_rejects_oversized_input(self):
        """Service rejects input exceeding max length."""
        service = InputSanitizerService()
        oversized = "a" * (service.MAX_STRING_LENGTH + 1)

        with pytest.raises(InputSanitizationError, match="maximum length"):
            service.sanitize_string(oversized)

    def test_sanitize_strips_null_bytes(self):
        """Service removes null bytes from input."""
        service = InputSanitizerService()
        result = service.sanitize_string("hello\x00world")

        assert "\x00" not in result
        assert "helloworld" in result


class TestSQLInjectionDetection:
    """Test SQL injection detection through the service port."""

    @pytest.mark.parametrize("payload", [
        "'; DROP TABLE detections; --",
        "1 OR 1=1",
        "UNION SELECT * FROM users",
        "'; DELETE FROM audit_trail; --",
        "1; INSERT INTO users VALUES ('hacker')",
    ])
    def test_detects_sql_injection_patterns(self, payload):
        """Service detects common SQL injection patterns."""
        service = InputSanitizerService()

        with pytest.raises(InputSanitizationError, match="SQL injection"):
            service.check_sql_injection(payload, "test_field")

    def test_allows_normal_strings(self):
        """Service allows normal text that is not an attack."""
        service = InputSanitizerService()
        # Should not raise
        service.check_sql_injection("vehicle", "object_class")
        service.check_sql_injection("dji_phantom_4", "camera_id")
        service.check_sql_injection("satellite_fire_api", "source")


class TestXSSDetection:
    """Test XSS detection through the service port."""

    @pytest.mark.parametrize("payload", [
        "<script>alert('xss')</script>",
        "javascript:alert(1)",
        "<img onerror=alert(1)>",
        "<iframe src='evil.com'>",
        "<svg onload=alert(1)>",
    ])
    def test_detects_xss_patterns(self, payload):
        """Service detects common XSS attack vectors."""
        service = InputSanitizerService()

        with pytest.raises(InputSanitizationError, match="XSS"):
            service.sanitize_string(payload, "test_field")


class TestPathTraversalDetection:
    """Test path traversal detection through the service port."""

    @pytest.mark.parametrize("payload", [
        "../../etc/passwd",
        "..\\windows\\system32",
        "%2e%2e%2f/etc/shadow",
    ])
    def test_detects_path_traversal(self, payload):
        """Service detects path traversal patterns."""
        service = InputSanitizerService()

        with pytest.raises(InputSanitizationError, match="path traversal"):
            service.check_path_traversal(payload)


class TestDictSanitization:
    """Test dictionary sanitization through the service port."""

    def test_sanitize_dict_escapes_string_values(self):
        """Service sanitizes all string values in dict."""
        service = InputSanitizerService()
        data = {
            "name": "normal text",
            "count": 42,
            "nested": {"label": "safe label"},
        }
        result = service.sanitize_dict(data)

        assert result["name"] == "normal text"
        assert result["count"] == 42
        assert result["nested"]["label"] == "safe label"

    def test_sanitize_dict_rejects_xss_in_values(self):
        """Service rejects XSS in dict values."""
        service = InputSanitizerService()
        data = {"name": "<script>alert(1)</script>"}

        with pytest.raises(InputSanitizationError, match="XSS"):
            service.sanitize_dict(data)

    def test_validate_detection_input_rejects_injection(self):
        """Service validates detection-specific fields."""
        service = InputSanitizerService()
        data = {"source": "'; DROP TABLE detections; --"}

        with pytest.raises(InputSanitizationError, match="SQL injection"):
            service.validate_detection_input(data)
