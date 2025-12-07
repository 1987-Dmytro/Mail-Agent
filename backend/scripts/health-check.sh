#!/bin/bash
# Health check for all Mail Agent services
# Author: Mail Agent Development Team
# Usage: ./scripts/health-check.sh

set -e

echo "🏥 Mail Agent Health Check"
echo ""
echo "=========================================="
echo ""

# Function to check service health
check_service() {
    local service_name="$1"
    local health_command="$2"

    printf "%-20s" "${service_name}:"

    if eval "${health_command}" > /dev/null 2>&1; then
        echo "✅ Healthy"
        return 0
    else
        echo "❌ Unhealthy"
        return 1
    fi
}

# Check Docker services
echo "🐳 Docker Services:"
echo ""
docker-compose ps

echo ""
echo "=========================================="
echo ""
echo "🔍 Service Health:"
echo ""

# Check each service
check_service "Backend API" "curl -f http://localhost:8000/health"
check_service "PostgreSQL" "docker-compose exec -T db pg_isready -U mailagent -d mailagent"
check_service "Redis" "docker-compose exec -T redis redis-cli ping"
check_service "Celery Worker" "docker-compose exec -T celery-worker celery -A app.celery inspect ping"
check_service "Flower" "curl -f http://localhost:5555"
check_service "Prometheus" "curl -f http://localhost:9090/-/healthy"
check_service "Grafana" "curl -f http://localhost:3000/api/health"

echo ""
echo "=========================================="
echo ""
echo "📊 Celery Tasks:"
echo ""
docker-compose exec celery-worker celery -A app.celery inspect active || echo "⚠️  Cannot inspect celery tasks"

echo ""
echo "=========================================="
echo ""
echo "💾 Volumes:"
echo ""
docker volume ls | grep backend || echo "No backend volumes found"

echo ""
echo "=========================================="
echo ""
