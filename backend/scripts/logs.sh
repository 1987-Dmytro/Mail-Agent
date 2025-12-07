#!/bin/bash
# View logs from Mail Agent services
# Author: Mail Agent Development Team
# Usage: ./scripts/logs.sh [service_name] [--tail N]

set -e

SERVICE="${1:-}"
TAIL_LINES="${3:-100}"

echo "📝 Mail Agent Logs"
echo ""

if [[ -z "$SERVICE" ]]; then
    echo "Available services:"
    echo "  app              - FastAPI backend"
    echo "  celery-worker    - Celery worker (email processing)"
    echo "  celery-beat      - Celery beat (periodic tasks)"
    echo "  flower           - Celery monitoring"
    echo "  db               - PostgreSQL"
    echo "  redis            - Redis"
    echo "  prometheus       - Prometheus"
    echo "  grafana          - Grafana"
    echo ""
    echo "Usage examples:"
    echo "  ./scripts/logs.sh app              # Follow app logs"
    echo "  ./scripts/logs.sh celery-worker    # Follow worker logs"
    echo "  ./scripts/logs.sh --tail 50        # Last 50 lines from all services"
    echo ""

    # Show recent logs from all services
    echo "Recent logs from all services (last 20 lines):"
    echo ""
    docker-compose logs --tail=20
else
    if [[ "$2" == "--tail" ]]; then
        echo "Last ${TAIL_LINES} lines from ${SERVICE}:"
        docker-compose logs --tail="${TAIL_LINES}" "${SERVICE}"
    else
        echo "Following logs from ${SERVICE} (Ctrl+C to exit):"
        echo ""
        docker-compose logs -f "${SERVICE}"
    fi
fi
