# Python 3.11 – required for PyTorch + sentence-transformers compatibility
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/model_cache \
    TRANSFORMERS_CACHE=/app/model_cache \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    imagemagick \
    ghostscript \
    ffmpeg \
    && (sed -i '/pattern=".*PDF.*"/s/rights="none"/rights="read|write"/g' /etc/ImageMagick-*/policy.xml || true) \
    && (sed -i '/pattern=".*LABEL.*"/s/rights="none"/rights="read|write"/g' /etc/ImageMagick-*/policy.xml || true) \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

COPY backend/requirements.prod.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.prod.txt

RUN mkdir -p /app/model_cache && chmod 777 /app/model_cache

COPY backend/ backend/

RUN chmod +x backend/entrypoint.sh backend/worker_entrypoint.sh

EXPOSE 8080

CMD ["./backend/entrypoint.sh"]

