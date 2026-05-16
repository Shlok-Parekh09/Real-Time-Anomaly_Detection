#!/bin/bash

# K-Nearest: Real-Time Anomaly & Forgery Detection
# Quick Start Script

echo "🔍 K-Nearest: Real-Time Anomaly & Forgery Detection"
echo "=================================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Check if dependencies are installed
if ! python3 -c "import streamlit" &> /dev/null
then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

echo "🚀 Starting Streamlit application..."
echo "📍 Application will open at: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the Streamlit app
streamlit run app.py
