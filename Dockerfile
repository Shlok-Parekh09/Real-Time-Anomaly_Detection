FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and general build
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY fraud_detection_system/backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY fraud_detection_system/backend/ .

# Create necessary directories
RUN mkdir -p uploads

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Start command — uses the main unified entry point
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
