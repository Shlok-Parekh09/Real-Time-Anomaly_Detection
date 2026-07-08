#!/bin/bash

# Start Ollama service in the background
echo "Starting Ollama server..."
ollama serve &

# Wait for Ollama to start
echo "Waiting for Ollama to be ready..."
sleep 5

# Optional: Ensure the model is available if the pull failed during build
# ollama pull qwen3.5:9b

# Start the FastAPI application on the Hugging Face Spaces required port (7860)
echo "Starting FastAPI app on port $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT
