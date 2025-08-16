# Use Python 3.13 slim image for smaller size and security
FROM python:3.13-slim

# Build arguments for versioning
ARG VERSION=dev
ARG COMMIT_SHA=unknown
ARG BUILD_DATE=unknown

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Set version metadata as environment variables
ENV APP_VERSION=${VERSION} \
    APP_COMMIT_SHA=${COMMIT_SHA} \
    APP_BUILD_DATE=${BUILD_DATE}

# Add OCI labels for metadata
LABEL org.opencontainers.image.title="AngelOne MCP Server" \
    org.opencontainers.image.description="FastMCP server exposing Angel One Smart API tools" \
    org.opencontainers.image.version=${VERSION} \
    org.opencontainers.image.revision=${COMMIT_SHA} \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.source="https://github.com/your-username/broker-buddy-mcp-server" \
    org.opencontainers.image.licenses="MIT"

# Create a non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Set working directory
WORKDIR /app

# Copy dependency files and README first for better layer caching
COPY pyproject.toml README.md ./

# Install UV for faster dependency management
RUN pip install uv

# Copy source code (needed for editable install)
COPY SmartApi/ ./SmartApi/
COPY src/ ./src/

# Install dependencies
RUN uv pip install --system -e .

# Create logs directory and set permissions
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port (default 9000, but can be overridden via build args or runtime)
EXPOSE 9000

# Health check (using environment variable for port with fallback)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${FASTMCP_PORT:-9000}${FASTMCP_PATH:-/mcp/}health || exit 1

# Run the application
CMD ["python", "-m", "angelone_mcp.server"]
