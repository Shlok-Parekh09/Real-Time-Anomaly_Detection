#!/bin/bash
set -e

echo "Starting Fraud Detection Backend with Local LLM..."
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "PORT: ${PORT:-8000}"

# Change to backend directory if needed
if [ -d "fraud_detection_system/backend" ]; then
    echo "Detected root directory, changing to backend..."
    cd fraud_detection_system/backend
fi

echo "Current directory: $(pwd)"
echo "Files in directory:"
ls -la

# Start the application
echo "Starting uvicorn..."
exec uvicorn main_local_llm:app --host 0.0.0.0 --port ${PORT:-8000}
