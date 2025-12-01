# Mail Agent - Docker Quick Start Guide

This guide helps you get the Mail Agent application running using Docker Compose with a single command.

## Prerequisites

- **Docker** (20.10+): [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** (2.0+): Included with Docker Desktop

Verify installation:
```bash
docker --version
docker-compose --version
```

## Quick Start (30 seconds)

### 1. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your database credentials (or use defaults):
```env
POSTGRES_DB=mailagent
POSTGRES_USER=mailagent
POSTGRES_PASSWORD=mailagent_dev_password_2024
```

### 2. Configure Backend

Ensure `backend/.env` exists with all required API keys:
```bash
cd backend
cp .env.example .env
# Edit backend/.env with your API keys (Gemini, Gmail OAuth, Telegram, etc.)
cd ..
```

**Required Variables in `backend/.env`:**
- `GEMINI_API_KEY` - Google Gemini API key
- `GMAIL_CLIENT_ID` - Gmail OAuth client ID
- `GMAIL_CLIENT_SECRET` - Gmail OAuth client secret
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `JWT_SECRET_KEY` - JWT signing key

### 3. Start All Services

From the project root:
```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Redis message broker (port 6379)
- Backend API (port 8000)
- Celery worker (background tasks)

### 4. Verify Services

Check all services are running:
```bash
docker-compose ps
```

Expected output:
```
NAME                     STATUS              PORTS
mailagent-backend        Up (healthy)        0.0.0.0:8000->8000/tcp
mailagent-celery-worker  Up (healthy)
mailagent-postgres       Up (healthy)        0.0.0.0:5432->5432/tcp
mailagent-redis          Up (healthy)        0.0.0.0:6379->6379/tcp
```

Test the API:
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

## Common Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

### Stop Services
```bash
docker-compose down
```

### Stop and Remove Volumes (Fresh Start)
```bash
docker-compose down -v
```

### Rebuild After Code Changes
```bash
docker-compose build
docker-compose up -d
```

### Run Database Migrations
```bash
docker-compose exec backend /app/.venv/bin/alembic upgrade head
```

### Access Database Shell
```bash
docker-compose exec postgres psql -U mailagent -d mailagent
```

### Execute Commands in Backend Container
```bash
docker-compose exec backend /app/.venv/bin/python -c "print('Hello')"
```

## Development Workflow

### Option 1: Full Docker (Recommended for New Developers)
All services in Docker:
```bash
docker-compose up -d
```

### Option 2: Hybrid (Local Backend + Docker Services)
Services only (database, redis):
```bash
docker-compose up -d postgres redis
```

Then run backend locally:
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Option 3: Frontend via Docker (Optional)
Uncomment frontend service in `docker-compose.yml` and run:
```bash
docker-compose up -d frontend
```

Frontend will be available at `http://localhost:3000`

## Service Architecture

```
┌─────────────────┐
│   Frontend      │ (Port 3000 - Optional)
│   (Next.js)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Backend API   │ (Port 8000)
│   (FastAPI)     │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐  ┌──────────┐
│Postgres│  │  Redis   │
│  (DB)  │  │ (Broker) │
└────────┘  └─────┬────┘
                  │
                  ▼
         ┌────────────────┐
         │ Celery Worker  │
         │ (Background)   │
         └────────────────┘
```

## Troubleshooting

### Services Won't Start
```bash
# Check logs for errors
docker-compose logs

# Remove old containers and try again
docker-compose down
docker-compose up -d
```

### Database Connection Errors
```bash
# Verify postgres is healthy
docker-compose ps postgres

# Check DATABASE_URL in backend/.env matches docker-compose settings
```

### Port Already in Use
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process or change port in docker-compose.yml
```

### Celery Worker Not Processing Tasks
```bash
# Check worker logs
docker-compose logs celery-worker

# Verify Redis connection
docker-compose exec backend /app/.venv/bin/celery -A app.celery inspect ping
```

### "Permission Denied" Errors
```bash
# Fix file permissions
chmod -R 755 backend/logs
```

## Production Deployment

For production:

1. **Use Managed Services** - Don't run postgres/redis in Docker
   ```yaml
   # Remove postgres and redis services
   # Use managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
   # Use managed Redis (AWS ElastiCache, Redis Cloud, etc.)
   ```

2. **Set Production Environment**
   ```env
   APP_ENV=production
   ```

3. **Use Secrets Management**
   - Store sensitive keys in AWS Secrets Manager, Vault, etc.
   - Never commit `.env` files to git

4. **Configure Resource Limits**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1'
         memory: 1G
   ```

5. **Set Up Monitoring**
   - Use the included Prometheus/Grafana services
   - Configure alerting for service health

## Environment Variables Reference

### Project Root `.env`
- `APP_ENV` - Environment (development/production)
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password

### Backend `.env` (See `backend/.env.example` for full list)
- `GEMINI_API_KEY` - Google Gemini API key
- `GMAIL_CLIENT_ID` - Gmail OAuth client ID
- `GMAIL_CLIENT_SECRET` - Gmail OAuth secret
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `JWT_SECRET_KEY` - JWT signing key
- `FRONTEND_URL` - Frontend URL for OAuth redirects

## Next Steps

1. Access API documentation: `http://localhost:8000/docs`
2. Run tests: `docker-compose exec backend /app/.venv/bin/pytest`
3. Create first user via API
4. Complete Gmail OAuth setup
5. Link Telegram bot

## Support

- Backend README: `backend/README.md`
- Architecture docs: `docs/architecture.md`
- PRD: `docs/PRD.md`
- Issues: File in project issue tracker

---

**Generated**: 2025-11-30
**Story**: 3-1-docker-compose-auto-start
