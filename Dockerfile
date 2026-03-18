# Use the production Dockerfile from the backend directory
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TRANSFORMERS_CACHE=/app/model_cache \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and use a virtual environment to avoid pip root warnings
RUN python -m venv /opt/venv

# Copy requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create cache directory for AI models
RUN mkdir -p /app/model_cache && chmod 777 /app/model_cache

# Copy backend application code
COPY backend/ .

# Expose port (Render uses 10000 by default or $PORT)
EXPOSE 10000

# Command to run the application with 1 worker to save RAM on Free Tier
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1
