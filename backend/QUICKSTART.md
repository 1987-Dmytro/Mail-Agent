# Mail Agent - Quick Start Guide

Быстрый старт для разработки и тестирования Mail Agent.

## 🎯 Текущая Конфигурация

### Запущенные Сервисы

| Сервис | URL | Описание |
|--------|-----|----------|
| **Frontend** | <http://localhost:3001> | Next.js UI (онбординг, dashboard) |
| **Backend API** | <http://localhost:8000> | FastAPI (REST API) |
| **API Docs** | <http://localhost:8000/docs> | Swagger/OpenAPI документация |
| **Flower** | <http://localhost:5555> | Celery monitoring (задачи, очереди) |
| **Grafana** | <http://localhost:3000> | Мониторинг метрик (admin/admin) |
| **Prometheus** | <http://localhost:9090> | Сбор метрик |
| **PostgreSQL** | localhost:5432 | База данных |
| **Redis** | localhost:6379 | Брокер сообщений Celery |

### Порты

- **3001** - Mail Agent UI (Frontend)
- **3000** - Grafana
- **8000** - Backend API
- **5555** - Flower (Celery)
- **5432** - PostgreSQL
- **6379** - Redis
- **9090** - Prometheus
- **8080** - cAdvisor

---

## 🚀 Запуск Всей Системы

### Быстрый Старт

```bash
cd backend
./scripts/start-all.sh
```

### Первый Запуск (с билдом)

```bash
./scripts/start-all.sh --build
```

### Проверка Статуса

```bash
docker-compose ps
```

Все сервисы должны быть в статусе `Up` или `Up (healthy)`.

---

## 🧪 Тестирование Онбординга

После запуска системы:

1. **Откройте браузер**: <http://localhost:3001>
2. **Регистрация**:
   - Email: любой валидный email
   - Password: минимум 8 символов
3. **Gmail OAuth**:
   - Нажмите "Connect Gmail"
   - Авторизуйтесь через Google
   - Разрешите доступ к Gmail
4. **Telegram Bot**:
   - Получите код для линковки
   - Отправьте `/start <код>` боту @June_25_AMB_bot
5. **Настройка Folders**:
   - Создайте категории для классификации
   - Или используйте дефолтные
6. **Готово!**
   - Dashboard покажет статистику
   - Система начнёт обработку писем каждые 2 минуты

---

## 🔍 Проверка Работоспособности

### Backend Health Check

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "components": {
    "api": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "celery": "healthy"
  }
}
```

---

## 🐛 Типичные Проблемы

### 1. Frontend показывает "No internet connection"

**Причина:** CORS не настроен для порта 3001

**Решение:**

```bash
# Проверить CORS
curl -v -H "Origin: http://localhost:3001" http://localhost:8000/health 2>&1 | grep access-control

# Если нет заголовка access-control-allow-origin:
# 1. Убедиться что в .env есть:
# ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

# 2. Пересоздать контейнер
docker-compose up -d --force-recreate app

# 3. Обновить страницу в браузере (Cmd+Shift+R)
```

### 2. База данных пустая (нет пользователей)

**Решение:** Пройдите онбординг через UI на <http://localhost:3001>

### 3. Celery не обрабатывает задачи

**Решение:**

```bash
# Проверить логи
docker-compose logs celery-worker celery-beat

# Перезапустить
docker-compose restart celery-worker celery-beat
```

---

## 📝 Логи

```bash
# Все сервисы (последние 20 строк)
./scripts/logs.sh

# Конкретный сервис
docker-compose logs -f app
docker-compose logs -f frontend
docker-compose logs -f celery-worker
```

---

## ⚙️ Важные Переменные Окружения

Файл: `backend/.env`

```bash
# Frontend & CORS (КРИТИЧНО!)
FRONTEND_URL=http://localhost:3001
ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

# Database
POSTGRES_DB=mailagent
POSTGRES_USER=mailagent
POSTGRES_PASSWORD=mailagent_dev_password_2024

# Telegram Bot
TELEGRAM_BOT_USERNAME=June_25_AMB_bot
```

**⚠️ После изменения .env:**

```bash
docker-compose up -d --force-recreate [service_name]
```

---

## 💡 Быстрые Команды

```bash
# Статус всех сервисов
docker-compose ps

# Перезапустить backend
docker-compose restart app

# Проверить здоровье БД
docker-compose exec db pg_isready -U mailagent -d mailagent

# Посмотреть активные Celery задачи
docker-compose exec celery-worker celery -A app.celery inspect active
```

---

## ✅ Чеклист для Разработки

- [ ] Все сервисы запущены (`docker-compose ps`)
- [ ] Backend health check работает (`curl localhost:8000/health`)
- [ ] Frontend открывается (<http://localhost:3001>)
- [ ] API docs доступны (<http://localhost:8000/docs>)
- [ ] Flower показывает воркеров (<http://localhost:5555>)
- [ ] CORS настроен (frontend может делать запросы к backend)

---

**Версия:** 0.1.0  
**Окружение:** Development  
**Последнее обновление:** 2025-12-07
