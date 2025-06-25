#!/bin/bash
# Build script for Render deployment
# This ensures consistent, reproducible builds

set -e  # Exit on any error

echo "📦 Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "🎭 Installing Playwright browsers..."
# Install only Chromium for faster builds and smaller size
playwright install chromium

echo "✅ Build completed successfully!" 