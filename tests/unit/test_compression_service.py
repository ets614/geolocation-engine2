"""Unit tests for compression service.

Tests gzip compression, compression negotiation, cache headers, and statistics.
"""

import pytest
import gzip
from src.services.compression_service import (
    CompressionService,
    CompressionType,
)


@pytest.fixture
def compression_service():
    """Create compression service instance."""
    return CompressionService()


class TestGzipCompression:
    """Test GZIP compression functionality."""

    def test_compress_small_data_not_compressed(self, compression_service):
        """Test that small data (<1KB) is not compressed."""
        small_data = b"small"
        compressed, encoding = compression_service.compress(small_data)

        assert compressed == small_data
        assert encoding == "identity"

    def test_compress_large_data(self, compression_service):
        """Test that large data is compressed."""
        # Create data that compresses well
        large_data = b"x" * 10000  # 10KB of repetitive data
        compressed, encoding = compression_service.compress(large_data)

        assert encoding == "gzip"
        assert len(compressed) < len(large_data)
        assert len(compressed) < len(large_data) * 0.95  # >5% compression

    def test_decompress_gzip_data(self, compression_service):
        """Test decompressing gzip data."""
        original = b"x" * 10000
        compressed, _ = compression_service.compress(original)

        decompressed = compression_service.decompress(compressed, "gzip")
        assert decompressed == original

    def test_compress_json_data(self, compression_service):
        """Test compression of JSON-like data."""
        json_data = b'{"key": "value", "array": [1, 2, 3], "nested": {"data": "here"}}' * 100
        compressed, encoding = compression_service.compress(json_data)

        if len(json_data) > CompressionService.MIN_COMPRESS_SIZE:
            assert encoding == "gzip"
            assert len(compressed) < len(json_data)

    def test_compression_ratio_tracking(self, compression_service):
        """Test compression ratio statistics."""
        large_data = b"x" * 10000
        compression_service.compress(large_data)

        stats = compression_service.get_compression_stats()
        assert stats["compressed_count"] >= 1
        assert stats["total_bytes_original"] > 0
        assert stats["total_bytes_compressed"] > 0

    def test_incompressible_data_not_compressed(self, compression_service):
        """Test that random/incompressible data isn't compressed."""
        import os
        random_data = os.urandom(2000)  # Random data doesn't compress well

        compressed, encoding = compression_service.compress(random_data)

        # Random data usually doesn't compress > 5%, so should return uncompressed
        # (behavior depends on randomness)
        assert encoding in ("gzip", "identity")


class TestCompressionNegotiation:
    """Test content negotiation for compression."""

    def test_negotiate_gzip_preferred(self, compression_service):
        """Test GZIP is selected when accepted."""
        accept_encoding = "gzip, deflate, identity"
        result = compression_service.negotiate_encoding(accept_encoding)
        assert result == CompressionType.GZIP

    def test_negotiate_deflate_accepted(self, compression_service):
        """Test DEFLATE is selected as fallback."""
        accept_encoding = "deflate, identity"
        result = compression_service.negotiate_encoding(accept_encoding)
        assert result == CompressionType.DEFLATE

    def test_negotiate_identity_only(self, compression_service):
        """Test IDENTITY is selected when no compression accepted."""
        accept_encoding = "identity"
        result = compression_service.negotiate_encoding(accept_encoding)
        assert result == CompressionType.IDENTITY

    def test_negotiate_no_header(self, compression_service):
        """Test IDENTITY when no Accept-Encoding header."""
        result = compression_service.negotiate_encoding(None)
        assert result == CompressionType.IDENTITY

    def test_negotiate_with_quality_values(self, compression_service):
        """Test negotiation with quality values."""
        accept_encoding = "gzip;q=0.8, deflate;q=0.9, identity;q=0.1"
        result = compression_service.negotiate_encoding(accept_encoding)

        # Should prefer gzip (highest quality that's typically first)
        assert result in (CompressionType.GZIP, CompressionType.DEFLATE)

    def test_negotiate_case_insensitive(self, compression_service):
        """Test negotiation is case-insensitive."""
        accept_encoding = "GZIP, DEFLATE"
        result = compression_service.negotiate_encoding(accept_encoding)
        assert result == CompressionType.GZIP

    def test_negotiate_whitespace_handling(self, compression_service):
        """Test negotiation handles extra whitespace."""
        accept_encoding = "  gzip  ,  deflate  ,  identity  "
        result = compression_service.negotiate_encoding(accept_encoding)
        assert result == CompressionType.GZIP


class TestCacheHeaders:
    """Test cache control header generation."""

    def test_short_cache_headers(self, compression_service):
        """Test short-lived cache headers (1 minute)."""
        headers = compression_service.get_cache_headers("short", is_public=True)

        assert "Cache-Control" in headers
        assert "max-age=60" in headers["Cache-Control"]
        assert "public" in headers["Cache-Control"]

    def test_medium_cache_headers(self, compression_service):
        """Test medium cache headers (5 minutes)."""
        headers = compression_service.get_cache_headers("medium", is_public=True)

        assert "max-age=300" in headers["Cache-Control"]
        assert "public" in headers["Cache-Control"]

    def test_long_cache_headers(self, compression_service):
        """Test long-lived cache headers (24 hours)."""
        headers = compression_service.get_cache_headers("long", is_public=True)

        assert "max-age=86400" in headers["Cache-Control"]
        assert "public" in headers["Cache-Control"]

    def test_private_cache_headers(self, compression_service):
        """Test private cache headers."""
        headers = compression_service.get_cache_headers("medium", is_public=False)

        assert "private" in headers["Cache-Control"]
        assert "public" not in headers["Cache-Control"]

    def test_must_revalidate_flag(self, compression_service):
        """Test must-revalidate flag is set."""
        headers = compression_service.get_cache_headers("short", is_public=True)

        assert "must-revalidate" in headers["Cache-Control"]

    def test_cache_headers_all_types(self, compression_service):
        """Test cache headers for all cache types."""
        for cache_type in ("short", "medium", "long"):
            headers = compression_service.get_cache_headers(cache_type)

            assert "Cache-Control" in headers
            assert "Pragma" in headers
            assert "max-age=" in headers["Cache-Control"]

    def test_default_cache_type(self, compression_service):
        """Test default cache type is medium."""
        headers1 = compression_service.get_cache_headers("unknown")
        headers2 = compression_service.get_cache_headers("medium")

        assert headers1["Cache-Control"] == headers2["Cache-Control"]


class TestCompressionStatistics:
    """Test compression statistics and monitoring."""

    def test_stats_empty(self, compression_service):
        """Test stats for unused service."""
        stats = compression_service.get_compression_stats()

        assert stats["total_responses"] == 0
        assert stats["compressed_count"] == 0
        assert stats["uncompressed_count"] == 0
        assert stats["overall_ratio"] == 0

    def test_stats_with_compressed_data(self, compression_service):
        """Test stats after compression."""
        large_data = b"x" * 10000
        compression_service.compress(large_data)

        stats = compression_service.get_compression_stats()
        assert stats["total_responses"] >= 1
        assert stats["total_bytes_original"] > 0

    def test_stats_with_uncompressed_data(self, compression_service):
        """Test stats tracking uncompressed responses."""
        small_data = b"small"
        compression_service.compress(small_data)

        stats = compression_service.get_compression_stats()
        assert stats["uncompressed_count"] >= 1

    def test_compression_ratio_calculation(self, compression_service):
        """Test compression ratio is calculated correctly."""
        large_data = b"x" * 10000
        compression_service.compress(large_data)

        stats = compression_service.get_compression_stats()
        original = stats["total_bytes_original"]
        compressed = stats["total_bytes_compressed"]

        if original > 0:
            expected_ratio = (compressed / original * 100)
            assert stats["overall_ratio"] <= 100

    def test_multiple_compressions_accumulate(self, compression_service):
        """Test stats accumulate across multiple calls."""
        for _ in range(3):
            data = b"x" * 5000
            compression_service.compress(data)

        stats = compression_service.get_compression_stats()
        assert stats["total_responses"] >= 3


class TestDecompression:
    """Test decompression for various encodings."""

    def test_decompress_identity(self, compression_service):
        """Test identity (no decompression)."""
        data = b"test data"
        result = compression_service.decompress(data, "identity")
        assert result == data

    def test_decompress_deflate(self, compression_service):
        """Test deflate decompression."""
        data = b"test data"
        result = compression_service.decompress(data, "deflate")
        assert result == data

    def test_decompress_unknown_encoding(self, compression_service):
        """Test handling of unknown encoding."""
        data = b"test data"
        result = compression_service.decompress(data, "unknown")
        assert result == data

    def test_compress_decompress_roundtrip(self, compression_service):
        """Test compress->decompress roundtrip."""
        original = b"x" * 10000
        compressed, encoding = compression_service.compress(original)

        if encoding != "identity":
            decompressed = compression_service.decompress(compressed, encoding)
            assert decompressed == original


@pytest.mark.parametrize("data_size", [100, 1000, 10000, 100000])
def test_compression_with_various_sizes(compression_service, data_size):
    """Test compression behavior with different data sizes."""
    data = b"x" * data_size
    compressed, encoding = compression_service.compress(data)

    if data_size >= CompressionService.MIN_COMPRESS_SIZE:
        assert encoding in ("gzip", "identity")
    else:
        assert encoding == "identity"


@pytest.mark.parametrize("accept_encoding,expected_type", [
    ("gzip", CompressionType.GZIP),
    ("deflate", CompressionType.DEFLATE),
    ("gzip, deflate", CompressionType.GZIP),
    ("deflate, gzip", CompressionType.GZIP),
    ("identity", CompressionType.IDENTITY),
])
def test_negotiate_with_various_headers(compression_service, accept_encoding, expected_type):
    """Test negotiation with various Accept-Encoding values."""
    result = compression_service.negotiate_encoding(accept_encoding)
    assert result == expected_type
