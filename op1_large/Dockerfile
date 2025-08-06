# Multi-stage build for op1_large
ARG PYTHON_VERSION=3.11
ARG DEBIAN_FRONTEND=noninteractive

FROM python:${PYTHON_VERSION}-slim as builder

# Install build dependencies for yajl2_c backend
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libyajl-dev \
    make \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements first for better caching
COPY op1_large/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Final stage
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

# Install runtime dependencies for yajl2_c
RUN apt-get update && apt-get install -y --no-install-recommends \
    libyajl2 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with configurable UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} appuser && \
    useradd -m -u ${USER_ID} -g appuser -s /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy shared directory (actual files, not symlinks)
COPY shared/ /app/shared/

# Copy op1_large application code
COPY op1_large/ /app/op1_large/

# Create json_worker directory and copy shared files
RUN mkdir -p /app/op1_large/json_worker && \
    cp /app/shared/streaming_parser.py /app/op1_large/json_worker/streaming_parser.py && \
    cp /app/shared/gpu_guard.py /app/op1_large/json_worker/gpu_guard.py

# Set Python path to include app directory
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set build-time labels
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.version=$VERSION \
      org.label-schema.name="json-lite-op1" \
      org.label-schema.description="JSON-Lite OP1 Large Processor"

# Create output directory
RUN mkdir -p /app/output && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command (can be overridden)
ENTRYPOINT ["python"]
CMD ["/app/op1_large/manual_processor.py"]