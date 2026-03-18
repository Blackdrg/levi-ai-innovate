# Use the production Dockerfile from the backend directory
FROM python:3.11-slim

# Copy the backend Dockerfile contents or just redirect
# For Render, we use render.yaml which specifies paths.
# For local building from root, this file serves as a entry point.

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]