#!/bin/bash
# Start all Mail Agent services
# Author: Mail Agent Development Team
# Usage: ./scripts/start-all.sh [--build]

set -e

echo "🚀 Starting Mail Agent Services..."
echo ""

# Check if --build flag is provided
if [[ "$1" == "--build" ]]; then
    echo "📦 Building Docker images..."
    docker-compose build
    echo ""
fi

# Step 1: Start database and redis first
echo "▶️  Starting database and redis..."
docker-compose up -d db redis

# Step 2: Wait for database to be healthy
echo "⏳ Waiting for database to be ready..."
until docker-compose exec -T db pg_isready -U mailagent -d mailagent > /dev/null 2>&1; do
    echo "   Database is not ready yet, waiting..."
    sleep 2
done
echo "✅ Database is ready!"

# Step 3: Run database migrations
echo "🔄 Running database migrations..."
docker-compose run --rm app alembic upgrade head
echo "✅ Migrations completed!"
echo ""

# Step 4: Start all remaining services
echo "▶️  Starting all services..."
docker-compose up -d

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🔗 Access Points:"
echo "   📧 Backend API:      http://localhost:8000"
echo "   📚 API Docs:         http://localhost:8000/docs"
echo "   🌸 Flower (Celery): http://localhost:5555"
echo "   📈 Grafana:          http://localhost:3000 (admin/admin)"
echo "   📊 Prometheus:       http://localhost:9090"
echo "   🗄️  PostgreSQL:       localhost:5432"
echo "   🔴 Redis:            localhost:6379"
echo ""
echo "📝 View logs:"
echo "   docker-compose logs -f [service_name]"
echo ""
echo "🛑 Stop all services:"
echo "   docker-compose down"
echo ""
