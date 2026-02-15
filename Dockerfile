# Multi-stage Dockerfile for Detection API
# Stage 1: Build dependencies
# Stage 2: Production runtime (minimal attack surface)

# --------------------------------------------------------------------------
# Stage 1: Builder
# --------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files first (cache layer)
COPY pyproject.toml ./
COPY requirements.txt* ./

# Install Python dependencies
RUN pip install --no-cache-dir --prefix=/install -e ".[dev]" 2>/dev/null || \
    pip install --no-cache-dir --prefix=/install \
    fastapi>=0.104.0 \
    "uvicorn[standard]>=0.24.0" \
    pydantic>=2.0.0 \
    python-dotenv>=1.0.0 \
    sqlalchemy>=2.0.0 \
    alembic>=1.12.0 \
    numpy>=1.24.0 \
    pyproj>=3.6.0 \
    aiohttp>=3.9.0 \
    PyJWT>=2.8.0 \
    prometheus-client>=0.19.0

# --------------------------------------------------------------------------
# Stage 2: Production Runtime
# --------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Security: run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    tini && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY pyproject.toml ./

# Create data directory for SQLite queue
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R appuser:appuser /app

# Build metadata
ARG VERSION=unknown
ARG BUILD_DATE=unknown
ARG GIT_COMMIT=unknown

LABEL org.opencontainers.image.title="detection-api" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.description="AI Detection to COP Integration Service" \
      org.opencontainers.image.vendor="Detection Platform Team"

ENV VERSION=${VERSION} \
    BUILD_DATE=${BUILD_DATE} \
    GIT_COMMIT=${GIT_COMMIT} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["tini", "--"]

# Start uvicorn with production settings
CMD ["python", "-m", "uvicorn", "src.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--access-log", \
     "--log-level", "info", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
