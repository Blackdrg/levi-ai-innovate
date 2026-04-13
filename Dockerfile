# 🛡️ LEVI-AI Sovereign OS v15.0-GA Production Dockerfile
# Multi-stage build for minimum surface area and maximum security.

# --- Stage 1: Build Dependencies ---
FROM python:3.11-slim-bookworm as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# --- Stage 2: Final Production Image ---
FROM python:3.11-slim-bookworm

WORKDIR /app

# Non-root user for security
RUN groupadd -r levi && useradd -r -g levi levi

# Install runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /home/levi/.local
ENV PATH=/home/levi/.local/bin:$PATH

# Copy application code
COPY . .

# Set ownership and permissions
RUN chown -R levi:levi /app
USER levi

# Healthcheck for orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Entrypoint utilizes uvicorn for high performance
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--limit-concurrency", "500"]
