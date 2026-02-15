"""Input validation and sanitization service."""

from pydantic import BaseModel, validator
import re

class RequestValidation(BaseModel):
    """Base validation schema for API requests."""
    
    @validator('*')
    def validate_no_sql_injection(cls, v):
        """Prevent SQL injection patterns."""
        if isinstance(v, str):
            sql_patterns = [
                r'(\bDROP\b|\bDELETE\b|\bINSERT\b|\bUPDATE\b)',
                r'(-{2}|/\*|\*/)',  # SQL comments
                r'(;\s*$)',  # Trailing semicolon
            ]
            for pattern in sql_patterns:
                if re.search(pattern, v, re.IGNORECASE):
                    raise ValueError(f'Potential SQL injection detected: {v}')
        return v
    
    @validator('*')
    def validate_no_xss(cls, v):
        """Prevent XSS attacks."""
        if isinstance(v, str):
            xss_patterns = [
                r'<script[^>]*>',
                r'javascript:',
                r'on\w+\s*=',
            ]
            for pattern in xss_patterns:
                if re.search(pattern, v, re.IGNORECASE):
                    raise ValueError(f'Potential XSS attack detected: {v}')
        return v

class GeolocationRequest(RequestValidation):
    """Geolocation API request validation."""
    latitude: float
    longitude: float
    accuracy: float = 10.0
