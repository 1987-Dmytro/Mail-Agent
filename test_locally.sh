#!/bin/bash

echo "🧪 Local Testing Script"
echo "======================"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Backend is not running on port 8000!"
    echo ""
    echo "Please start the backend first:"
    echo "  cd backend"
    echo "  ./start_test_server.sh"
    echo ""
    exit 1
fi

echo "✅ Backend is running"
echo ""

# Run frontend tests
echo "🧪 Running frontend unit tests..."
cd frontend
npm run test:run

echo ""
echo "✅ Tests complete!"

