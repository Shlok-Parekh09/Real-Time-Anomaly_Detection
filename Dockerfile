FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY fraud_detection_system/backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY fraud_detection_system/backend/ .

# Create directories
RUN mkdir -p uploads .cache

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/.cache
ENV PORT=8000

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "main_local_llm:app", "--host", "0.0.0.0", "--port", "8000"]
