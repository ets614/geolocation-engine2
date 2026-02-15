"""Compression service for API response optimization.

Provides gzip compression, content negotiation, and cache header management
for efficient data transmission.
"""

import gzip
import logging
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class CompressionType(Enum):
    """Supported compression types."""
    GZIP = "gzip"
    DEFLATE = "deflate"
    IDENTITY = "identity"


class CompressionService:
    """Handle response compression and cache headers."""

    # Compression thresholds
    MIN_COMPRESS_SIZE = 1024  # Only compress if > 1KB
    COMPRESSION_LEVEL = 6  # Default gzip compression level (0-9)

    def __init__(self):
        """Initialize compression service."""
        self.stats = {
            "compressed": 0,
            "uncompressed": 0,
            "bytes_original": 0,
            "bytes_compressed": 0,
        }

    def compress(self, data: bytes, compression_type: CompressionType = CompressionType.GZIP) -> Tuple[bytes, str]:
        """Compress data using specified algorithm.

        Args:
            data: Data to compress
            compression_type: Compression algorithm to use

        Returns:
            Tuple of (compressed_data, content_encoding)
        """
        if len(data) < self.MIN_COMPRESS_SIZE:
            return data, "identity"

        if compression_type == CompressionType.GZIP:
            compressed = gzip.compress(data, compresslevel=self.COMPRESSION_LEVEL)
            ratio = len(compressed) / len(data)

            if ratio < 0.95:  # Only use if >5% compression
                self.stats["compressed"] += 1
                self.stats["bytes_original"] += len(data)
                self.stats["bytes_compressed"] += len(compressed)
                logger.debug(f"GZIP: {len(data)} -> {len(compressed)} bytes ({ratio:.2%})")
                return compressed, "gzip"

        # Return uncompressed if compression not efficient
        self.stats["uncompressed"] += 1
        self.stats["bytes_original"] += len(data)
        return data, "identity"

    def decompress(self, data: bytes, content_encoding: str) -> bytes:
        """Decompress data.

        Args:
            data: Compressed data
            content_encoding: Encoding type (gzip, deflate, identity)

        Returns:
            Decompressed data
        """
        if content_encoding == "gzip":
            return gzip.decompress(data)
        elif content_encoding in ("deflate", "identity"):
            return data
        else:
            logger.warning(f"Unknown encoding: {content_encoding}")
            return data

    def negotiate_encoding(self, accept_encoding: Optional[str]) -> CompressionType:
        """Negotiate compression based on Accept-Encoding header.

        Args:
            accept_encoding: Accept-Encoding header value

        Returns:
            Preferred compression type
        """
        if not accept_encoding:
            return CompressionType.IDENTITY

        accepted = accept_encoding.lower().split(",")
        accepted = [enc.split(";")[0].strip() for enc in accepted]

        # Order of preference
        for compression in [CompressionType.GZIP, CompressionType.DEFLATE]:
            if compression.value in accepted:
                return compression

        return CompressionType.IDENTITY

    def get_cache_headers(self, cache_type: str, is_public: bool = True) -> dict:
        """Generate cache headers for response.

        Args:
            cache_type: Type of cache (short, medium, long)
            is_public: Whether cache is public or private

        Returns:
            Dictionary of cache headers
        """
        cache_configs = {
            "short": {"max_age": 60, "description": "1 minute"},  # Health, dynamic
            "medium": {"max_age": 300, "description": "5 minutes"},  # API responses
            "long": {"max_age": 86400, "description": "24 hours"},  # Static content
        }

        config = cache_configs.get(cache_type, cache_configs["medium"])
        scope = "public" if is_public else "private"

        return {
            "Cache-Control": f"{scope}, max-age={config['max_age']}, must-revalidate",
            "Pragma": "cache" if is_public else "no-cache",
        }

    def get_compression_stats(self) -> dict:
        """Get compression statistics.

        Returns:
            Dictionary with compression metrics
        """
        total = self.stats["compressed"] + self.stats["uncompressed"]
        original = self.stats["bytes_original"]
        compressed = self.stats["bytes_compressed"]

        return {
            "total_responses": total,
            "compressed_count": self.stats["compressed"],
            "uncompressed_count": self.stats["uncompressed"],
            "total_bytes_original": original,
            "total_bytes_compressed": compressed,
            "overall_ratio": (compressed / original * 100) if original > 0 else 0,
        }
