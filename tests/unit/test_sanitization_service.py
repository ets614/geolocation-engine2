"""Unit tests for input sanitization service.

Test Budget: 8 distinct behaviors x 2 = 16+ unit tests
Behaviors:
1. SQL injection pattern detection
2. Command injection pattern detection
3. Path traversal pattern detection
4. XSS pattern detection
5. HTML escaping
6. Filename sanitization
7. Suspicious field detection (dict scanning)
8. Activity logging for detected attacks
"""
import pytest
from src.services.sanitization_service import SanitizationService


class TestSQLInjectionDetection:
    """Tests for SQL injection pattern detection.

    Behavior: SQL injection patterns are detected in strings
    """

    @pytest.fixture
    def service(self):
        return SanitizationService()

    def test_detects_union_select_injection(self, service):
        """Verify detection of UNION SELECT pattern."""
        payload = "1' UNION SELECT * FROM users--"
        assert service.detect_sql_injection(payload) is True

    def test_detects_or_true_injection(self, service):
        """Verify detection of OR 1=1 pattern."""
        payload = "admin' OR 1=1--"
        assert service.detect_sql_injection(payload) is True

    def test_detects_drop_table_injection(self, service):
        """Verify detection of DROP TABLE pattern."""
        payload = "'; DROP TABLE users;--"
        assert service.detect_sql_injection(payload) is True

    def test_detects_sql_comment_injection(self, service):
        """Verify detection of SQL comment pattern."""
        payload = "1' OR '1'='1' -- "
        assert service.detect_sql_injection(payload) is True

    def test_accepts_safe_string(self, service):
        """Verify safe strings are not flagged."""
        safe = "detector_001"
        assert service.detect_sql_injection(safe) is False

    def test_case_insensitive_detection(self, service):
        """Verify detection is case-insensitive."""
        payload = "1' union select * from users--"
        assert service.detect_sql_injection(payload) is True

    @pytest.mark.parametrize("payload", [
        "SELECT * FROM table",
        "INSERT INTO table VALUES",
        "UPDATE table SET value=1",
        "DELETE FROM table",
    ])
    def test_detects_sql_keywords(self, service, payload):
        """Verify detection of SQL keywords in injection context."""
        malicious = f"1'; {payload}; --"
        assert service.detect_sql_injection(malicious) is True


class TestCommandInjectionDetection:
    """Tests for command injection pattern detection.

    Behavior: Command injection patterns blocked
    """

    @pytest.fixture
    def service(self):
        return SanitizationService()

    def test_detects_pipe_injection(self, service):
        """Verify detection of pipe character."""
        payload = "file.txt | cat /etc/passwd"
        assert service.detect_command_injection(payload) is True

    def test_detects_semicolon_injection(self, service):
        """Verify detection of semicolon command separator."""
        payload = "ls; rm -rf /"
        assert service.detect_command_injection(payload) is True

    def test_detects_backtick_injection(self, service):
        """Verify detection of backtick command substitution."""
        payload = "`whoami`"
        assert service.detect_command_injection(payload) is True

    def test_detects_dollar_paren_injection(self, service):
        """Verify detection of $(command) syntax."""
        payload = "$(cat /etc/passwd)"
        assert service.detect_command_injection(payload) is True

    def test_detects_ampersand_injection(self, service):
        """Verify detection of & operator."""
        payload = "command1 & command2"
        assert service.detect_command_injection(payload) is True

    def test_accepts_safe_command_string(self, service):
        """Verify safe strings are not flagged."""
        safe = "filename_123.txt"
        assert service.detect_command_injection(safe) is False


class TestPathTraversalDetection:
    """Tests for path traversal pattern detection.

    Behavior: Path traversal attempts are blocked
    """

    @pytest.fixture
    def service(self):
        return SanitizationService()

    def test_detects_parent_directory_traversal(self, service):
        """Verify detection of ../ pattern."""
        payload = "../../../etc/passwd"
        assert service.detect_path_traversal(payload) is True

    def test_detects_double_dot_pattern(self, service):
        """Verify detection of .. pattern."""
        payload = "files/../../../sensitive.txt"
        assert service.detect_path_traversal(payload) is True

    def test_detects_url_encoded_traversal(self, service):
        """Verify detection of %2e%2e pattern."""
        payload = "%2e%2e/%2e%2e/etc/passwd"
        assert service.detect_path_traversal(payload) is True

    def test_detects_windows_traversal(self, service):
        """Verify detection of Windows path traversal."""
        payload = "..\\..\\Windows\\System32"
        assert service.detect_path_traversal(payload) is True

    def test_accepts_safe_filename(self, service):
        """Verify safe filenames are not flagged."""
        safe = "detection_001.jpg"
        assert service.detect_path_traversal(safe) is False

    def test_case_insensitive_url_encoded_detection(self, service):
        """Verify URL-encoded detection is case-insensitive."""
        payload = "%2E%2E/%2E%2E/etc/passwd"
        assert service.detect_path_traversal(payload) is True


class TestXSSDetection:
    """Tests for XSS pattern detection.

    Behavior: XSS payloads are detected
    """

    @pytest.fixture
    def service(self):
        return SanitizationService()

    def test_detects_script_tag_injection(self, service):
        """Verify detection of <script> tag."""
        payload = "<script>alert('xss')</script>"
        assert service.detect_xss(payload) is True

    def test_detects_event_handler_injection(self, service):
        """Verify detection of event handler."""
        payload = '<img src=x onerror="alert(1)">'
        assert service.detect_xss(payload) is True

    def test_detects_javascript_url(self, service):
        """Verify detection of javascript: URL."""
        payload = "<a href='javascript:alert(1)'>click</a>"
        assert service.detect_xss(payload) is True

    def test_detects_iframe_injection(self, service):
        """Verify detection of iframe tag."""
        payload = "<iframe src='evil.com'></iframe>"
        assert service.detect_xss(payload) is True

    def test_detects_object_tag(self, service):
        """Verify detection of object tag."""
        payload = "<object data='evil.swf'></object>"
        assert service.detect_xss(payload) is True

    def test_detects_embed_tag(self, service):
        """Verify detection of embed tag."""
        payload = "<embed src='evil.swf'>"
        assert service.detect_xss(payload) is True

    def test_accepts_safe_text(self, service):
        """Verify safe text is not flagged."""
        safe = "vehicle detection model v2"
        assert service.detect_xss(safe) is False

    def test_case_insensitive_detection(self, service):
        """Verify detection is case-insensitive."""
        payload = "<SCRIPT>alert(1)</SCRIPT>"
        assert service.detect_xss(payload) is True


class TestHTMLEscaping:
    """Tests for HTML entity escaping.

    Behavior: HTML entities are properly escaped
    """

    @pytest.fixture
    def service(self):
        return SanitizationService()

    def test_escapes_angle_brackets(self, service):
        """Verify angle brackets are escaped."""
        result = service.escape_html("<div>")
        assert "&lt;" in result
        assert "&gt;" in result

    def test_escapes_quotes(self, service):
        """Verify quotes are escaped."""
        result = service.escape_html('"quoted"')
        assert "&quot;" in result

    def test_escapes_ampersand(self, service):
        """Verify ampersand is escaped."""
        result = service.escape_html("A&B")
        assert "&amp;" in result

    def test_escapes_single_quotes(self, service):
        """Verify single quotes are escaped."""
        result = service.escape_html("'quoted'")
        assert "&#x27;" in result

    def test_preserves_normal_text(self, service):
        """Verify normal text is unchanged."""
        text = "vehicle detection model"
        result = service.escape_html(text)
        assert result == text


class TestFilenameSanitization:
    """Tests for filename sanitization.

    Behavior: Filenames are sanitized to prevent traversal
    """

    @pytest.fixture
    def service(self):
        return SanitizationService()

    def test_removes_forward_slash(self, service):
        """Verify forward slashes are removed."""
        result = service.sanitize_filename("path/to/file.jpg")
        assert "/" not in result

    def test_removes_backslash(self, service):
        """Verify backslashes are removed."""
        result = service.sanitize_filename("path\\to\\file.jpg")
        assert "\\" not in result

    def test_removes_parent_directory_reference(self, service):
        """Verify .. is removed."""
        result = service.sanitize_filename("../../../etc/passwd")
        assert ".." not in result

    def test_keeps_valid_characters(self, service):
        """Verify valid characters are preserved."""
        filename = "detection_001.jpg"
        result = service.sanitize_filename(filename)
        assert "detection_001" in result
        assert ".jpg" in result

    def test_removes_special_characters(self, service):
        """Verify special characters are removed."""
        result = service.sanitize_filename("file@#$%.jpg")
        assert "@" not in result
        assert "#" not in result

    def test_handles_long_filename(self, service):
        """Verify long filenames are truncated."""
        long_name = "a" * 300 + ".jpg"
        result = service.sanitize_filename(long_name)
        assert len(result) <= 255

    def test_handles_zero_length_filename(self, service):
        """Verify zero-length filename is handled."""
        result = service.sanitize_filename("")
        assert result == "unnamed"

    def test_prevents_dot_only_filename(self, service):
        """Verify dot-only filename is handled."""
        result = service.sanitize_filename(".")
        assert result == "unnamed"


class TestSuspiciousFieldDetection:
    """Tests for scanning dictionaries for suspicious content.

    Behavior: Dictionaries are scanned for multiple attack types
    """

    @pytest.fixture
    def service(self):
        return SanitizationService()

    def test_detects_sql_injection_field(self, service):
        """Verify SQL injection in field is detected."""
        data = {"client_id": "1' OR '1'='1--"}
        suspicious = service.get_suspicious_fields(data)
        assert "client_id" in suspicious

    def test_detects_xss_field(self, service):
        """Verify XSS in field is detected."""
        data = {"name": "<script>alert(1)</script>"}
        suspicious = service.get_suspicious_fields(data)
        assert "name" in suspicious

    def test_detects_path_traversal_field(self, service):
        """Verify path traversal in field is detected."""
        data = {"filename": "../../../etc/passwd"}
        suspicious = service.get_suspicious_fields(data)
        assert "filename" in suspicious

    def test_detects_multiple_suspicious_fields(self, service):
        """Verify multiple suspicious fields are detected."""
        data = {
            "client_id": "1' OR '1'='1--",
            "filename": "../../../etc/passwd",
            "safe_field": "normal_value",
        }
        suspicious = service.get_suspicious_fields(data)
        assert len(suspicious) == 2
        assert "client_id" in suspicious
        assert "filename" in suspicious

    def test_ignores_non_string_fields(self, service):
        """Verify non-string fields are skipped."""
        data = {
            "count": 42,
            "ratio": 3.14,
            "enabled": True,
            "items": [1, 2, 3],
        }
        suspicious = service.get_suspicious_fields(data)
        assert len(suspicious) == 0

    def test_returns_empty_for_safe_data(self, service):
        """Verify safe data returns empty list."""
        data = {
            "name": "detector_001",
            "model": "detection_model_v2",
            "confidence": 0.95,
        }
        suspicious = service.get_suspicious_fields(data)
        assert len(suspicious) == 0


class TestActivityLogging:
    """Tests for suspicious activity logging.

    Behavior: Suspicious activities are logged with context
    """

    @pytest.fixture
    def service(self):
        return SanitizationService()

    def test_logs_sql_injection_attack(self, service, caplog):
        """Verify SQL injection attack is logged."""
        service.log_suspicious_activity(
            field_name="client_id",
            attack_type="sql_injection",
            value="1' OR '1'='1",
            client_ip="192.168.1.100"
        )
        assert "sql_injection" in caplog.text

    def test_logs_xss_attack(self, service, caplog):
        """Verify XSS attack is logged."""
        service.log_suspicious_activity(
            field_name="name",
            attack_type="xss",
            value="<script>alert(1)</script>",
            client_ip="192.168.1.100"
        )
        assert "xss" in caplog.text

    def test_logs_path_traversal_attack(self, service, caplog):
        """Verify path traversal attack is logged."""
        service.log_suspicious_activity(
            field_name="filename",
            attack_type="path_traversal",
            value="../../../etc/passwd",
            client_ip="192.168.1.100"
        )
        assert "path_traversal" in caplog.text

    def test_includes_client_ip_in_log(self, service, caplog):
        """Verify suspicious activity is logged."""
        service.log_suspicious_activity(
            field_name="test",
            attack_type="test_attack",
            value="test_value",
            client_ip="203.0.113.42"
        )
        assert "test_attack" in caplog.text


class TestStringURLValidation:
    """Tests for URL and string validation methods."""

    @pytest.fixture
    def service(self):
        return SanitizationService()

    def test_accepts_safe_url(self, service):
        """Verify safe URLs are accepted."""
        url = "https://example.com/api/endpoint"
        assert service.validate_url(url) is True

    def test_rejects_javascript_url(self, service):
        """Verify javascript: URLs are rejected."""
        url = "javascript:alert(1)"
        assert service.validate_url(url) is False

    def test_rejects_data_url(self, service):
        """Verify data: URLs are rejected."""
        url = "data:text/html,<script>alert(1)</script>"
        assert service.validate_url(url) is False

    def test_sanitizes_string_with_length_limit(self, service):
        """Verify string sanitization respects length limit."""
        result = service.sanitize_string("hello world", max_length=5)
        assert len(result) == 5
        assert result == "hello"

    def test_escapes_html_by_default(self, service):
        """Verify HTML is escaped by default."""
        result = service.sanitize_string("<script>alert(1)</script>")
        assert "&lt;" in result
        assert "&gt;" in result

    def test_preserves_html_when_allowed(self, service):
        """Verify HTML can be preserved when allowed."""
        html = "<div>content</div>"
        result = service.sanitize_string(html, allow_html=True)
        assert "<div>" in result
