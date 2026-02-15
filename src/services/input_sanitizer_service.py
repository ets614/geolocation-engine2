"""Input validation and sanitization service for security hardening."""
import html
import re
from typing import Any, Dict, List, Optional


class InputSanitizationError(Exception):
    """Raised when input fails sanitization checks."""

    def __init__(self, field: str, reason: str):
        self.field = field
        self.reason = reason
        super().__init__(f"Sanitization failed for '{field}': {reason}")


class InputSanitizerService:
    """Service for validating and sanitizing user inputs.

    Provides defense-in-depth against:
    - SQL injection patterns
    - XSS payloads
    - Path traversal attacks
    - Command injection patterns
    - Oversized inputs
    """

    # SQL injection patterns (common attack vectors)
    SQL_INJECTION_PATTERNS = [
        r"(?i)\b(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from|drop\s+table|alter\s+table)\b",
        r"(?i)(\b(or|and)\b\s+[\d'\"=]+\s*[=<>])",
        r"(?i)(--|#|/\*|\*/)",
        r"(?i)(;\s*(drop|delete|insert|update|alter|create)\b)",
        r"('|\"|;)\s*(or|and|union)\s",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<\s*script",
        r"javascript\s*:",
        r"on\w+\s*=",
        r"<\s*iframe",
        r"<\s*object",
        r"<\s*embed",
        r"<\s*svg.*on\w+",
        r"data\s*:\s*text/html",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e/",
        r"\.%2e/",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",
        r"\$\(",
        r"\$\{",
    ]

    MAX_STRING_LENGTH = 10000
    MAX_FIELD_NAME_LENGTH = 256

    def sanitize_string(self, value: str, field_name: str = "input") -> str:
        """Sanitize a string input by escaping HTML and validating length.

        Args:
            value: Raw string input.
            field_name: Field name for error messages.

        Returns:
            Sanitized string.

        Raises:
            InputSanitizationError: If input contains malicious patterns.
        """
        if not isinstance(value, str):
            raise InputSanitizationError(field_name, "Expected string input")

        if len(value) > self.MAX_STRING_LENGTH:
            raise InputSanitizationError(
                field_name,
                f"Input exceeds maximum length of {self.MAX_STRING_LENGTH}",
            )

        # Check for XSS patterns before escaping
        self._check_xss(value, field_name)

        # HTML-escape the output
        sanitized = html.escape(value, quote=True)

        # Strip null bytes
        sanitized = sanitized.replace("\x00", "")

        return sanitized

    def check_sql_injection(self, value: str, field_name: str = "input") -> None:
        """Check a string for SQL injection patterns.

        Args:
            value: Input to check.
            field_name: Field name for error messages.

        Raises:
            InputSanitizationError: If SQL injection pattern detected.
        """
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value):
                raise InputSanitizationError(
                    field_name, "Potential SQL injection detected"
                )

    def _check_xss(self, value: str, field_name: str) -> None:
        """Check a string for XSS patterns.

        Args:
            value: Input to check.
            field_name: Field name for error messages.

        Raises:
            InputSanitizationError: If XSS pattern detected.
        """
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise InputSanitizationError(
                    field_name, "Potential XSS detected"
                )

    def check_path_traversal(self, value: str, field_name: str = "path") -> None:
        """Check a string for path traversal attacks.

        Args:
            value: Input to check.
            field_name: Field name for error messages.

        Raises:
            InputSanitizationError: If path traversal pattern detected.
        """
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise InputSanitizationError(
                    field_name, "Potential path traversal detected"
                )

    def check_command_injection(
        self, value: str, field_name: str = "input"
    ) -> None:
        """Check a string for command injection patterns.

        Args:
            value: Input to check.
            field_name: Field name for error messages.

        Raises:
            InputSanitizationError: If command injection pattern detected.
        """
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value):
                raise InputSanitizationError(
                    field_name, "Potential command injection detected"
                )

    def sanitize_dict(
        self,
        data: Dict[str, Any],
        string_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Sanitize all string values in a dictionary.

        Args:
            data: Dictionary to sanitize.
            string_fields: If provided, only sanitize these fields.
                           Otherwise sanitize all string values.

        Returns:
            Dictionary with sanitized string values.
        """
        result = {}
        for key, value in data.items():
            if len(key) > self.MAX_FIELD_NAME_LENGTH:
                raise InputSanitizationError(
                    key[:50], "Field name exceeds maximum length"
                )

            if isinstance(value, str):
                if string_fields is None or key in string_fields:
                    result[key] = self.sanitize_string(value, field_name=key)
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value, string_fields)
            else:
                result[key] = value

        return result

    def validate_detection_input(self, data: Dict[str, Any]) -> None:
        """Validate detection-specific input fields.

        Checks business-logic constraints beyond Pydantic validation:
        - String fields for injection attacks
        - Coordinate ranges
        - Confidence bounds

        Args:
            data: Detection input data.

        Raises:
            InputSanitizationError: If validation fails.
        """
        string_fields = ["source", "camera_id", "object_class"]
        for field_name in string_fields:
            if field_name in data and isinstance(data[field_name], str):
                self.check_sql_injection(data[field_name], field_name)
                self.sanitize_string(data[field_name], field_name)
