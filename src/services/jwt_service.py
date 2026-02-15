"""JWT authentication service for API security."""
import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any


class JWTService:
    """Service for JWT token generation and validation."""

    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        """Initialize JWT service.

        Args:
            secret_key: Secret key for signing tokens. Defaults to JWT_SECRET_KEY env var.
            algorithm: Algorithm for signing (default: HS256).
        """
        self.secret_key = secret_key or os.getenv(
            "JWT_SECRET_KEY",
            "your-secret-key-change-in-production"
        )
        self.algorithm = algorithm

    def generate_token(
        self,
        subject: str,
        expires_in_minutes: int = 60,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a JWT token.

        Args:
            subject: Subject claim (e.g., user ID or client ID)
            expires_in_minutes: Token expiration time in minutes
            additional_claims: Additional claims to include in token

        Returns:
            str: Signed JWT token

        Raises:
            ValueError: If subject is empty
        """
        if not subject:
            raise ValueError("Subject cannot be empty")

        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=expires_in_minutes)

        payload = {
            "sub": subject,
            "iat": now,
            "exp": expires,
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Dict: Decoded token payload

        Raises:
            ValueError: If token is invalid or expired
        """
        if not token:
            raise ValueError("Token cannot be empty")

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    def extract_subject(self, token: str) -> str:
        """Extract subject from a JWT token.

        Args:
            token: JWT token

        Returns:
            str: Subject claim value

        Raises:
            ValueError: If token is invalid
        """
        payload = self.verify_token(token)
        return payload.get("sub", "")

    def refresh_token(self, token: str, expires_in_minutes: int = 60) -> str:
        """Refresh a JWT token by issuing a new one with the same claims.

        The original token must still be valid (not expired).

        Args:
            token: Existing valid JWT token to refresh.
            expires_in_minutes: Expiration for the new token.

        Returns:
            str: New JWT token with refreshed expiration.

        Raises:
            ValueError: If original token is invalid or expired.
        """
        payload = self.verify_token(token)
        subject = payload.get("sub")
        if not subject:
            raise ValueError("Token missing subject claim")

        # Carry forward non-standard claims
        additional_claims = {
            k: v for k, v in payload.items()
            if k not in ("sub", "iat", "exp")
        }

        return self.generate_token(
            subject=subject,
            expires_in_minutes=expires_in_minutes,
            additional_claims=additional_claims if additional_claims else None,
        )
