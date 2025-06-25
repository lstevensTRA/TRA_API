#!/bin/bash
# Startup script for Render deployment

set -e  # Exit on any error

echo "🚀 Starting TRA API Backend..."

# Set Python path to include current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start the FastAPI application
echo "📡 Starting uvicorn server..."
python -m uvicorn server:app --host 0.0.0.0 --port $PORT 