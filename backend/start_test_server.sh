#!/bin/bash

echo "🔧 Starting backend server for local testing..."
echo ""

# Load test environment variables
export $(cat .env.test | grep -v '^#' | xargs)

# Start uvicorn
echo "🚀 Starting uvicorn on http://localhost:8000"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

