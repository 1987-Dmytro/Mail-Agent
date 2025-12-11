# Mail Agent - Docker Setup Инструкция

## 🚀 Быстрый старт

### Запуск всей системы
```bash
docker-compose up -d
```

### Остановка всех сервисов
```bash
docker-compose down
```

### Полная перезагрузка (с удалением данных)
```bash
docker-compose down -v
docker-compose up -d
```

## 📦 Запущенные сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| **Backend (FastAPI)** | 8000 | API сервер |
| **Frontend (Next.js)** | 3000 | Web интерфейс |
| **PostgreSQL** | 5432 | База данных |
| **Redis** | 6379 | Кэш и очередь задач |
| **ChromaDB** | 8001 | Векторная БД для RAG |
| **Celery Worker** | - | Фоновые задачи |
| **Celery Beat** | - | Планировщик задач |

## 🔗 Полезные ссылки

- **API документация (Swagger):** http://localhost:8000/docs
- **API документация (ReDoc):** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health
- **Frontend:** http://localhost:3000

## 🛠 Управление сервисами

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f celery-worker
```

### Проверка статуса
```bash
docker-compose ps
```

### Перезапуск конкретного сервиса
```bash
docker-compose restart backend
docker-compose restart frontend
```

### Пересборка образов
```bash
# Пересобрать все образы
docker-compose build --no-cache

# Пересобрать конкретный сервис
docker-compose build --no-cache backend
```

## 🗄 Работа с базой данных

### Подключение к PostgreSQL
```bash
docker-compose exec postgres psql -U mailagent -d mailagent
```

### Запуск миграций
```bash
docker-compose exec backend /app/.venv/bin/alembic upgrade head
```

### Откат миграций
```bash
docker-compose exec backend /app/.venv/bin/alembic downgrade -1
```

### Создание новой миграции
```bash
docker-compose exec backend /app/.venv/bin/alembic revision -m "описание миграции"
```

## 🧪 Тестирование

### Запуск тестов backend
```bash
docker-compose exec backend /app/.venv/bin/pytest
```

### Запуск конкретного теста
```bash
docker-compose exec backend /app/.venv/bin/pytest tests/test_file.py
```

### Проверка покрытия тестами
```bash
docker-compose exec backend /app/.venv/bin/pytest --cov=app
```

## 📊 Мониторинг Celery

### Проверка статуса Celery worker
```bash
docker-compose exec backend /app/.venv/bin/celery -A app.celery inspect ping
```

### Просмотр активных задач
```bash
docker-compose exec backend /app/.venv/bin/celery -A app.celery inspect active
```

### Просмотр запланированных задач
```bash
docker-compose exec backend /app/.venv/bin/celery -A app.celery inspect scheduled
```

## 🔧 Полезные команды

### Выполнение команд внутри контейнера
```bash
# Backend
docker-compose exec backend bash

# Frontend
docker-compose exec frontend sh

# PostgreSQL
docker-compose exec postgres bash
```

### Очистка неиспользуемых ресурсов Docker
```bash
# Удалить неиспользуемые образы
docker image prune -a

# Удалить неиспользуемые volumes
docker volume prune

# Полная очистка
docker system prune -a --volumes
```

## 🐛 Решение проблем

### Сервисы не запускаются
```bash
# Проверить логи
docker-compose logs

# Пересобрать образы
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Проблемы с портами
```bash
# Найти процесс, использующий порт
lsof -i :8000
lsof -i :3000

# Убить процесс
kill -9 <PID>
```

### Ошибки подключения к базе данных
```bash
# Проверить статус PostgreSQL
docker-compose ps postgres

# Перезапустить PostgreSQL
docker-compose restart postgres

# Проверить логи
docker-compose logs postgres
```

### Проблемы с Celery
```bash
# Проверить статус worker
docker-compose ps celery-worker

# Перезапустить worker
docker-compose restart celery-worker

# Проверить Redis
docker-compose exec redis redis-cli ping
```

## 📝 Конфигурация

### Основные файлы конфигурации
- `docker-compose.yml` - Конфигурация Docker Compose
- `backend/.env` - Переменные окружения backend
- `frontend/.env.local` - Переменные окружения frontend
- `backend/Dockerfile` - Dockerfile для backend
- `frontend/Dockerfile` - Dockerfile для frontend

### Важные переменные окружения (backend/.env)
```env
# API ключи
GEMINI_API_KEY=your_gemini_api_key
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# База данных (для Docker используется 'postgres')
POSTGRES_HOST=postgres
DATABASE_URL=postgresql+psycopg://mailagent:mailagent_dev_password_2024@postgres:5432/mailagent

# JWT
JWT_SECRET_KEY=your_jwt_secret_key
```

## 🎯 Быстрые тесты

### Проверка API
```bash
# Health check
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/

# API документация
open http://localhost:8000/docs
```

### Проверка Frontend
```bash
open http://localhost:3000
```

### Проверка базы данных
```bash
docker-compose exec postgres psql -U mailagent -d mailagent -c "SELECT version();"
```

### Проверка Redis
```bash
docker-compose exec redis redis-cli ping
```

## 🔐 Безопасность

### Рекомендации для продакшена
1. **Изменить пароли по умолчанию** в `backend/.env`
2. **Использовать secrets management** (AWS Secrets Manager, Vault)
3. **Не коммитить `.env` файлы** в git
4. **Использовать HTTPS** для продакшена
5. **Настроить firewall** и ограничить доступ к портам
6. **Включить логирование и мониторинг**

## 📚 Дополнительные ресурсы

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Celery Documentation](https://docs.celeryproject.org/)

## ✅ Статус системы

После успешного запуска:

```bash
docker-compose ps
```

Должны быть запущены все 7 сервисов:
- ✅ mailagent-backend (healthy)
- ✅ mailagent-frontend (running)
- ✅ mailagent-postgres (healthy)
- ✅ mailagent-redis (healthy)
- ✅ mailagent-chromadb (running)
- ✅ mailagent-celery-worker (healthy)
- ✅ mailagent-celery-beat (running)

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs`
2. Проверьте статус: `docker-compose ps`
3. Изучите [DOCKER_QUICKSTART.md](./DOCKER_QUICKSTART.md)
4. Обратитесь к документации проекта в папке `docs/`

---

**Дата создания:** 2025-12-11
**Версия:** 1.0.0
