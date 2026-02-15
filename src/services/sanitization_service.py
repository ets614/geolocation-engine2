"""Input sanitization service for preventing injection attacks."""
import re
import html
from typing import Optional, Dict, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SanitizationService:
    """Service for sanitizing user inputs against injection attacks."""

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bor\b\s+1\s*=\s*1)",
        r"(\bor\b\s+1\s*=\s*1\b)",
        r"('[\s]*or[\s]*')",  # ' OR '
        r"(\bdrop\b.*\b(table|database)\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(;.*\b(select|drop|insert|update|delete|create)\b)",
        r"(--)",
        r"(/\*.*\*/)",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]<>\\]",  # Shell metacharacters
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",  # ../ traversal
        r"\.\.",   # .. directory
        r"%2e%2e",  # URL encoded ..
        r"\.\.\\",  # Windows traversal
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"on\w+\s*=",  # Event handlers: onclick=, onerror=, etc.
        r"javascript:",
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    def __init__(self):
        """Initialize sanitization service."""
        self.compiled_sql_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.SQL_INJECTION_PATTERNS
        ]
        self.compiled_cmd_patterns = [
            re.compile(pattern) for pattern in self.COMMAND_INJECTION_PATTERNS
        ]
        self.compiled_path_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.PATH_TRAVERSAL_PATTERNS
        ]
        self.compiled_xss_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.XSS_PATTERNS
        ]

    def detect_sql_injection(self, value: str) -> bool:
        """Detect SQL injection patterns in input.

        Args:
            value: Input string to check

        Returns:
            True if SQL injection pattern detected, False otherwise
        """
        if not isinstance(value, str):
            return False

        for pattern in self.compiled_sql_patterns:
            if pattern.search(value):
                logger.warning(
                    "SQL injection pattern detected",
                    extra={"input_sample": value[:100]}
                )
                return True
        return False

    def detect_command_injection(self, value: str) -> bool:
        """Detect command injection patterns in input.

        Args:
            value: Input string to check

        Returns:
            True if command injection pattern detected, False otherwise
        """
        if not isinstance(value, str):
            return False

        for pattern in self.compiled_cmd_patterns:
            if pattern.search(value):
                logger.warning(
                    "Command injection pattern detected",
                    extra={"input_sample": value[:100]}
                )
                return True
        return False

    def detect_path_traversal(self, value: str) -> bool:
        """Detect path traversal patterns in input.

        Args:
            value: Input string to check

        Returns:
            True if path traversal pattern detected, False otherwise
        """
        if not isinstance(value, str):
            return False

        for pattern in self.compiled_path_patterns:
            if pattern.search(value):
                logger.warning(
                    "Path traversal pattern detected",
                    extra={"input_sample": value[:100]}
                )
                return True
        return False

    def detect_xss(self, value: str) -> bool:
        """Detect XSS patterns in input.

        Args:
            value: Input string to check

        Returns:
            True if XSS pattern detected, False otherwise
        """
        if not isinstance(value, str):
            return False

        for pattern in self.compiled_xss_patterns:
            if pattern.search(value):
                logger.warning(
                    "XSS pattern detected",
                    extra={"input_sample": value[:100]}
                )
                return True
        return False

    def escape_html(self, value: str) -> str:
        """Escape HTML entities in input.

        Args:
            value: Input string to escape

        Returns:
            HTML-escaped string
        """
        if not isinstance(value, str):
            return str(value)

        return html.escape(value, quote=True)

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and illegal characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        if not isinstance(filename, str):
            return "unknown"

        # Remove path separators
        filename = filename.replace("/", "").replace("\\", "")

        # Remove parent directory references
        filename = filename.replace("..", "")

        # Keep only alphanumeric, dash, underscore, and extension
        filename = re.sub(r"[^a-zA-Z0-9._-]", "", filename)

        # Prevent zero-length filename
        if not filename or filename == ".":
            return "unnamed"

        # Cap length
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = name[:250] + ("." + ext if ext else "")

        return filename

    def validate_file_path(self, file_path: str, base_directory: Optional[str] = None) -> bool:
        """Validate file path doesn't escape intended directory.

        Args:
            file_path: File path to validate
            base_directory: Base directory files should be within

        Returns:
            True if path is safe, False if traversal detected
        """
        if not isinstance(file_path, str):
            return False

        if self.detect_path_traversal(file_path):
            return False

        if base_directory:
            try:
                resolved = Path(base_directory).resolve() / file_path
                base = Path(base_directory).resolve()
                return str(resolved).startswith(str(base))
            except (ValueError, OSError):
                return False

        return True

    def validate_url(self, url: str) -> bool:
        """Validate URL is safe (not javascript: or data:).

        Args:
            url: URL to validate

        Returns:
            True if URL is safe, False if dangerous
        """
        if not isinstance(url, str):
            return False

        dangerous_schemes = ["javascript:", "data:", "vbscript:"]
        url_lower = url.lower().strip()

        for scheme in dangerous_schemes:
            if url_lower.startswith(scheme):
                logger.warning("Dangerous URL scheme detected", extra={"url": url[:50]})
                return False

        return True

    def sanitize_string(
        self,
        value: str,
        allow_html: bool = False,
        max_length: Optional[int] = None
    ) -> str:
        """Sanitize string input with optional length limiting.

        Args:
            value: Input string
            allow_html: If False, escape HTML entities
            max_length: Maximum length to allow

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)

        # Trim whitespace
        value = value.strip()

        # Apply length limit
        if max_length and len(value) > max_length:
            value = value[:max_length]

        # Escape HTML if not allowed
        if not allow_html:
            value = self.escape_html(value)

        return value

    def get_suspicious_fields(self, data: Dict) -> List[str]:
        """Scan dictionary for suspicious fields and return list of field names.

        Args:
            data: Dictionary to scan

        Returns:
            List of field names with suspicious content
        """
        suspicious = []

        for key, value in data.items():
            if not isinstance(value, str):
                continue

            if self.detect_sql_injection(value):
                suspicious.append(key)
            elif self.detect_command_injection(value):
                suspicious.append(key)
            elif self.detect_path_traversal(value):
                suspicious.append(key)
            elif self.detect_xss(value):
                suspicious.append(key)

        return suspicious

    def log_suspicious_activity(
        self,
        field_name: str,
        attack_type: str,
        value: str,
        client_ip: Optional[str] = None
    ) -> None:
        """Log suspicious activity for audit trail.

        Args:
            field_name: Name of suspicious field
            attack_type: Type of attack detected (sql_injection, xss, etc.)
            value: Suspicious value
            client_ip: Client IP address
        """
        logger.warning(
            f"Suspicious activity detected: {attack_type}",
            extra={
                "field": field_name,
                "attack_type": attack_type,
                "value_sample": value[:100] if value else "",
                "client_ip": client_ip,
            }
        )
