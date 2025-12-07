# Mail Agent Services Management

Comprehensive guide for managing Mail Agent backend services using Docker Compose.

## 🚀 Quick Start

### Start All Services

```bash
./scripts/start-all.sh
```

Or with fresh build:

```bash
./scripts/start-all.sh --build
```

### Stop All Services

```bash
./scripts/stop-all.sh
```

Or stop and clean volumes (⚠️ **data loss**):

```bash
./scripts/stop-all.sh --clean
```

---

## 📦 Services Overview

### Core Services

| Service | Port | Description | Dependencies |
|---------|------|-------------|--------------|
| **app** | 8000 | FastAPI backend (main API) | db, redis |
| **db** | 5432 | PostgreSQL 18 database | - |
| **redis** | 6379 | Redis (Celery broker) | - |

### Background Processing

| Service | Port | Description | Dependencies |
|---------|------|-------------|--------------|
| **celery-worker** | - | Background tasks (email processing, indexing) | db, redis |
| **celery-beat** | - | Periodic tasks scheduler | db, redis |
| **flower** | 5555 | Celery monitoring dashboard | redis, celery-worker |

### Frontend

| Service | Port | Description | Dependencies |
|---------|------|-------------|--------------|
| **frontend** | 3001 | Next.js UI application (Docker: 3000→3001) | app |

**Note**: Frontend runs on port 3000 inside the container, mapped to port 3001 on the host to avoid conflict with Grafana (port 3000).

### Monitoring & Observability

| Service | Port | Description | Dependencies |
|---------|------|-------------|--------------|
| **prometheus** | 9090 | Metrics collection | - |
| **grafana** | 3000 | Metrics visualization (admin/admin) | prometheus |
| **cadvisor** | 8080 | Container metrics | - |

---

## 🔗 Access Points

After starting services, access them at:

- **Frontend (Mail Agent UI)**: http://localhost:3001
  - User registration and login
  - Gmail OAuth connection
  - Telegram bot linking
  - Email classification and management

- **Backend API**: http://localhost:8000
  - Interactive docs: http://localhost:8000/docs
  - Health check: http://localhost:8000/health

- **Flower (Celery)**: http://localhost:5555
  - View active tasks, workers, and queues

- **Grafana**: http://localhost:3000
  - Default credentials: `admin/admin`

- **Prometheus**: http://localhost:9090
  - Metrics and targets

---

## 📊 Periodic Tasks (Celery Beat)

Scheduled tasks run automatically via `celery-beat`:

| Task | Schedule | Description |
|------|----------|-------------|
| **poll-all-users** | Every 2 minutes | Poll Gmail for new emails |
| **send-batch-notifications** | Daily 18:00 UTC | Send batched Telegram notifications |
| **send-daily-digest** | Daily 18:30 UTC | Send daily email digests |
| **cleanup-old-vector-embeddings** | Daily 03:00 UTC | Remove embeddings >90 days old |

---

## 💾 Persistent Data

Data is stored in Docker volumes:

| Volume | Purpose | Path |
|--------|---------|------|
| **postgres-data** | PostgreSQL database | `/var/lib/postgresql/data` |
| **redis-data** | Redis persistence | `/data` |
| **chromadb-data** | Vector database embeddings (bind mount) | `/app/backend/data/chromadb` |
| **celery-beat-schedule** | Beat scheduler state | `/app/celerybeat-schedule` |
| **grafana-storage** | Grafana dashboards | `/var/lib/grafana` |

### Backup Volumes

```bash
# Backup PostgreSQL
docker-compose exec db pg_dump -U mailagent mailagent > backup.sql

# Backup ChromaDB
docker run --rm -v backend_chromadb-data:/data -v $(pwd):/backup alpine tar czf /backup/chromadb-backup.tar.gz -C /data .
```

### Restore Volumes

```bash
# Restore PostgreSQL
docker-compose exec -T db psql -U mailagent mailagent < backup.sql

# Restore ChromaDB
docker run --rm -v backend_chromadb-data:/data -v $(pwd):/backup alpine tar xzf /backup/chromadb-backup.tar.gz -C /data
```

---

## 🔍 Monitoring & Logs

### View Logs

```bash
# All services (last 20 lines)
./scripts/logs.sh

# Specific service (follow mode)
./scripts/logs.sh app
./scripts/logs.sh celery-worker
./scripts/logs.sh celery-beat

# Last N lines
./scripts/logs.sh app --tail 100
```

### Health Check

```bash
./scripts/health-check.sh
```

### Monitor Celery Tasks

```bash
# Active tasks
docker-compose exec celery-worker celery -A app.celery inspect active

# Registered tasks
docker-compose exec celery-worker celery -A app.celery inspect registered

# Worker stats
docker-compose exec celery-worker celery -A app.celery inspect stats
```

---

## 🛠️ Development Workflow

### Local Development (without Docker)

If you prefer to run backend locally:

```bash
# Start dependencies only
docker-compose up -d db redis

# Run backend
uv run uvicorn app.main:app --reload

# Run celery worker (separate terminal)
uv run celery -A app.celery worker --loglevel=info

# Run celery beat (separate terminal)
uv run celery -A app.celery beat --loglevel=info
```

### Hot Reload

With Docker Compose, code changes are automatically detected via volume mounts:

```bash
# Restart specific service after changes
docker-compose restart app
docker-compose restart celery-worker
```

### Run Tests

```bash
# Inside container
docker-compose exec app pytest tests/ -v

# Or locally
cd backend
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" uv run pytest tests/ -v
```

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check service logs
docker-compose logs [service_name]

# Check service status
docker-compose ps

# Rebuild service
docker-compose build [service_name]
docker-compose up -d [service_name]
```

### Database Connection Issues

```bash
# Check DB health
docker-compose exec db pg_isready -U mailagent -d mailagent

# Restart DB
docker-compose restart db

# Check migrations
docker-compose exec app alembic current
docker-compose exec app alembic upgrade head
```

### Celery Tasks Not Running

```bash
# Check worker status
docker-compose exec celery-worker celery -A app.celery inspect ping

# Check beat scheduler
docker-compose logs celery-beat

# Restart workers
docker-compose restart celery-worker celery-beat
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Frontend Connection Issues ("No internet connection")

If the frontend shows "No internet connection" error:

```bash
# 1. Check if backend is accessible
curl http://localhost:8000/health

# 2. Verify CORS configuration
curl -v -H "Origin: http://localhost:3001" http://localhost:8000/health 2>&1 | grep access-control

# Should see: access-control-allow-origin: http://localhost:3001

# 3. If CORS header is missing, check ALLOWED_ORIGINS in .env
grep ALLOWED_ORIGINS /path/to/backend/.env

# 4. Update ALLOWED_ORIGINS to include frontend port
# Edit .env: ALLOWED_ORIGINS="...,http://localhost:3001,..."

# 5. Recreate backend container to apply changes
docker-compose up -d --force-recreate app

# 6. Refresh browser (Cmd+Shift+R / Ctrl+Shift+R)
```

**Common Causes:**
- Backend CORS not configured for frontend port
- Frontend running on different port than expected (3001 vs 3000)
- Environment variables not reloaded after `.env` changes
- Browser cache showing stale error

---

## 🔒 Security Notes

### Production Deployment

Before deploying to production:

1. **Change default passwords** in `.env`:
   - `POSTGRES_PASSWORD`
   - `JWT_SECRET_KEY`
   - Grafana admin password

2. **Use secrets management**:
   - Store sensitive values in Docker secrets or environment
   - Never commit `.env` to git

3. **Enable SSL/TLS**:
   - Use reverse proxy (nginx/traefik) with SSL certificates
   - Set `SECURE_COOKIES=true`

4. **Restrict network access**:
   - Remove exposed ports for internal services
   - Use firewall rules

---

## 📚 Additional Resources

- **Architecture Documentation**: `/docs/architecture.md`
- **API Documentation**: http://localhost:8000/docs (when running)
- **Celery Documentation**: https://docs.celeryproject.org/
- **ChromaDB Documentation**: https://docs.trychroma.com/

---

## ⚙️ Environment Variables

Key environment variables (defined in `.env`):

```bash
# Database
POSTGRES_DB=mailagent
POSTGRES_USER=mailagent
POSTGRES_PASSWORD=mailagent_dev_password_2024
DATABASE_URL=postgresql+psycopg://mailagent:mailagent_dev_password_2024@db:5432/mailagent

# Redis
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Application
APP_ENV=development
JWT_SECRET_KEY=supersecretkeythatshouldbechangedforproduction

# Frontend & CORS
FRONTEND_URL=http://localhost:3001
ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

# Polling
POLLING_INTERVAL_SECONDS=120

# ChromaDB
CHROMADB_PERSIST_DIRECTORY=/app/backend/data/chromadb

# Gmail OAuth
GMAIL_CLIENT_ID=<your-google-oauth-client-id>
GMAIL_CLIENT_SECRET=<your-google-oauth-client-secret>
GMAIL_REDIRECT_URI=http://localhost:8000/api/v1/auth/gmail/callback

# Telegram Bot
TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
```

### Important Notes

- **ALLOWED_ORIGINS**: Must include all ports where frontend runs (3000 for Grafana, 3001 for Mail Agent UI)
- **FRONTEND_URL**: Must match the actual frontend port (3001 for Docker setup)
- After changing `.env`, recreate containers: `docker-compose up -d --force-recreate [service_name]`

---

## 📞 Support

For issues or questions:

1. Check logs: `./scripts/logs.sh [service]`
2. Run health check: `./scripts/health-check.sh`
3. Review architecture docs in `/docs`
4. Open GitHub issue with logs and error details
