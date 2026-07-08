FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    zstd \
    dos2unix \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama binary (requires root)
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set up a new user named "user" with user ID 1000 (Required by Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user

# Set home and path for the user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    OLLAMA_MODELS=/home/user/.ollama/models

# Set working directory
WORKDIR $HOME/app

# Pre-pull is handled dynamically at runtime now
RUN bash -c "ollama serve & OLLAMA_PID=\$!; \
    sleep 5; \
    kill \$OLLAMA_PID; \
    wait \$OLLAMA_PID || true"

# Copy requirements
COPY --chown=user requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user . .

# Fix Windows line endings and make executable
RUN dos2unix start.sh && chmod +x start.sh

# Create necessary directories
RUN mkdir -p uploads

# Set environment variables for Hugging Face Spaces
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV OLLAMA_BASE_URL=http://localhost:11434
ENV USE_LOCAL_LLM=True
ENV DATASET_DIR=/home/user/app/dataset

EXPOSE 7860

# Start command using explicit bash to avoid execution permission issues
CMD ["bash", "start.sh"]
