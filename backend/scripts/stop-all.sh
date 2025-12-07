#!/bin/bash
# Stop all Mail Agent services
# Author: Mail Agent Development Team
# Usage: ./scripts/stop-all.sh [--clean]

set -e

echo "🛑 Stopping Mail Agent Services..."
echo ""

if [[ "$1" == "--clean" ]]; then
    echo "⚠️  Cleaning volumes (all data will be lost)..."
    docker-compose down -v
    echo "✅ Services stopped and volumes cleaned!"
else
    docker-compose down
    echo "✅ Services stopped (data preserved in volumes)"
fi

echo ""
echo "💡 To remove volumes and clean data:"
echo "   ./scripts/stop-all.sh --clean"
echo ""
