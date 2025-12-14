# 🚀 Mail Agent - Deployment Guide

Полное руководство по развёртыванию Mail Agent на Oracle Cloud (бесплатно) + Vercel.

---

## 📋 Содержание

1. [Архитектура](#архитектура)
2. [Требования](#требования)
3. [Настройка Oracle Cloud](#настройка-oracle-cloud)
4. [Настройка GitHub](#настройка-github)
5. [Настройка Vercel](#настройка-vercel)
6. [Развёртывание](#развёртывание)
7. [Git Workflow](#git-workflow)
8. [Мониторинг](#мониторинг)
9. [Troubleshooting](#troubleshooting)

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    ORACLE CLOUD (FREE)                       │
├─────────────────────────────────────────────────────────────┤
│  VM #1 - STAGING (ARM A1 - 2 OCPU, 12GB RAM)               │
│  ├── Backend (FastAPI) + Celery + Redis                     │
│  ├── PostgreSQL → Autonomous DB (Free)                      │
│  └── Monitoring: Prometheus + Grafana                       │
│                                                              │
│  VM #2 - PRODUCTION (ARM A1 - 2 OCPU, 12GB RAM)            │
│  ├── Backend (FastAPI) + Celery + Redis                     │
│  ├── PostgreSQL → Autonomous DB (Free)                      │
│  └── Nginx (Reverse Proxy + SSL)                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       VERCEL (FREE)                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend - Next.js                                          │
│  ├── develop → staging.yourdomain.com                       │
│  └── main → yourdomain.com                                  │
└─────────────────────────────────────────────────────────────┘

💰 Стоимость: $0/месяц
```

---

## Требования

### Аккаунты
- ✅ GitHub аккаунт
- ✅ Oracle Cloud аккаунт (Always Free Tier)
- ✅ Vercel аккаунт (бесплатный)
- ✅ Домен (опционально, для production SSL)

### Локальная машина
- Git
- SSH client
- Доступ к интернету

---

## Настройка Oracle Cloud

### 1. Регистрация

1. Перейдите на https://www.oracle.com/cloud/free/
2. Зарегистрируйтесь (нужна кредитная карта для верификации)
3. Получите:
   - $300 credits на 30 дней
   - Always Free Tier навсегда

### 2. Создание Staging VM

```bash
Oracle Console → Compute → Instances → Create Instance

Настройки:
- Name: mailagent-staging
- Image: Ubuntu 22.04 (Minimal)
- Shape: VM.Standard.A1.Flex (Ampere ARM)
  - OCPU: 2
  - Memory: 12 GB
- Networking: Создать новую VCN (mailagent-vcn)
- SSH Keys: Загрузить ваш публичный SSH ключ
- Boot Volume: 50 GB

✅ Убедитесь, что выбран Always Free eligible
```

### 3. Создание Production VM

Повторите шаги выше, но:
- Name: `mailagent-production`
- Используйте ту же VCN

### 4. Настройка Security List

```bash
Oracle Console → Networking → Virtual Cloud Networks
→ mailagent-vcn → Security Lists → Default Security List

Добавить Ingress Rules:
┌──────────────────────────────────────────────────┐
│ Port │ Protocol │ Source      │ Description      │
├──────────────────────────────────────────────────┤
│ 22   │ TCP      │ 0.0.0.0/0   │ SSH             │
│ 80   │ TCP      │ 0.0.0.0/0   │ HTTP            │
│ 443  │ TCP      │ 0.0.0.0/0   │ HTTPS           │
│ 8000 │ TCP      │ 0.0.0.0/0   │ Backend API     │
│ 3000 │ TCP      │ 0.0.0.0/0   │ Grafana         │
│ 5555 │ TCP      │ 0.0.0.0/0   │ Flower          │
└──────────────────────────────────────────────────┘
```

### 5. Создание Autonomous Databases

**Staging Database:**
```bash
Oracle Console → Autonomous Database → Create Database

- Workload Type: Transaction Processing
- Deployment: Serverless
- Database Name: mailagent_staging
- Database Version: 19c
- OCPU: 1 (Always Free)
- Storage: 20 GB (Always Free)
- Auto Scaling: OFF
- Admin Password: [создайте сложный пароль]

✅ Поставьте галочку "Always Free"
```

**Production Database:**
Повторите для `mailagent_production`

**Сохраните connection strings:**
- Oracle Console → DB → DB Connection → Download Wallet
- Откройте `tnsnames.ora` и скопируйте connection string
- Формат: `postgresql://admin:password@host:1522/db_name`

### 6. Настройка VM

**Подключитесь к каждой VM:**

```bash
# Замените IP и путь к ключу
ssh -i ~/.ssh/oracle_key ubuntu@<VM_PUBLIC_IP>
```

**Запустите setup скрипт:**

```bash
# Staging VM
wget https://raw.githubusercontent.com/1987-Dmytro/Mail-Agent/main/backend/scripts/setup-vm.sh
bash setup-vm.sh staging

# Production VM
wget https://raw.githubusercontent.com/1987-Dmytro/Mail-Agent/main/backend/scripts/setup-vm.sh
bash setup-vm.sh production

# ВАЖНО: После setup перелогиньтесь!
exit
ssh -i ~/.ssh/oracle_key ubuntu@<VM_PUBLIC_IP>
```

### 7. Настройка Nginx с SSL (Production)

```bash
# На production VM
bash ~/Mail-Agent/backend/scripts/setup-nginx.sh production api.yourdomain.com
```

---

## Настройка GitHub

### 1. GitHub Secrets

```bash
GitHub → Settings → Secrets and variables → Actions → New repository secret
```

**Создайте следующие секреты:**

```yaml
# Oracle Cloud
STAGING_VM_IP: <IP staging VM>
PRODUCTION_VM_IP: <IP production VM>
ORACLE_SSH_PRIVATE_KEY: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  [ваш приватный SSH ключ]
  -----END OPENSSH PRIVATE KEY-----

# Databases
STAGING_DATABASE_URL: postgresql://admin:pass@host:1522/mailagent_staging
PRODUCTION_DATABASE_URL: postgresql://admin:pass@host:1522/mailagent_production

# Application Secrets
JWT_SECRET_KEY: <generate with: openssl rand -base64 32>
ENCRYPTION_KEY: <generate with: openssl rand -base64 32>

# Gmail OAuth (получите в Google Console)
GMAIL_CLIENT_ID: xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET: xxx

# AI APIs
GEMINI_API_KEY: <from Google AI Studio>
GROQ_API_KEY: <from Groq Console>

# Frontend URLs
STAGING_API_URL: http://<staging-vm-ip>:8000
PRODUCTION_API_URL: https://api.yourdomain.com
```

### 2. Branch Protection Rules

```bash
GitHub → Settings → Branches → Add branch protection rule
```

**Для `main` ветки:**
```yaml
Branch name pattern: main

Protect matching branches:
☑ Require a pull request before merging
  ☑ Require approvals: 1
  ☑ Dismiss stale pull request approvals
☑ Require status checks to pass before merging
  ☑ Require branches to be up to date
  Required status checks:
    - backend-ci / lint
    - backend-ci / test
    - frontend-ci / lint
    - frontend-ci / test
☑ Require conversation resolution before merging
☑ Do not allow bypassing the above settings
```

**Для `develop` ветки:**
Повторите те же настройки.

### 3. Environments

```bash
GitHub → Settings → Environments → New environment
```

**Staging Environment:**
```yaml
Name: staging
Environment protection rules:
  - No protection (auto-deploy)
Environment secrets:
  - (используются repository secrets)
```

**Production Environment:**
```yaml
Name: production
Environment protection rules:
  ☑ Required reviewers: [ваш username]
  ☑ Wait timer: 0 minutes
Environment secrets:
  - (используются repository secrets)
```

---

## Настройка Vercel

### 1. Import Project

1. Перейдите на https://vercel.com
2. Sign in with GitHub
3. Import `Mail-Agent` repository
4. Настройте:
   ```yaml
   Framework Preset: Next.js
   Root Directory: frontend
   Build Command: npm run build
   Output Directory: .next
   Install Command: npm ci
   ```

### 2. Environment Variables

**Production (main branch):**
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
INTERNAL_API_URL=https://api.yourdomain.com
NODE_ENV=production
```

**Preview (develop branch):**
```bash
NEXT_PUBLIC_API_URL=http://<staging-vm-ip>:8000
INTERNAL_API_URL=http://<staging-vm-ip>:8000
NODE_ENV=development
```

### 3. Git Integration

```bash
Vercel → Project Settings → Git

Production Branch: main
Preview Branches: develop
```

---

## Развёртывание

### Первое развёртывание

1. **Commit и Push workflows:**
   ```bash
   cd Mail-Agent
   git checkout develop
   git add .github/workflows backend/scripts
   git commit -m "ci: Add CI/CD workflows and deployment scripts"
   git push origin develop
   ```

2. **Автоматический деплой в Staging:**
   - GitHub Actions автоматически запустит deploy-backend-staging.yml
   - Vercel автоматически задеплоит frontend

3. **Проверьте Staging:**
   ```bash
   # Backend
   curl http://<staging-vm-ip>:8000/health

   # Frontend
   # Откройте Vercel preview URL
   ```

4. **Деплой в Production:**
   ```bash
   # Создайте PR: develop → main
   git checkout main
   git merge develop
   git push origin main

   # Или через GitHub UI:
   # Create Pull Request: develop → main
   # После approval и merge → автодеплой в production
   ```

---

## Git Workflow

### Разработка новой функции

```bash
# 1. Создайте feature ветку от develop
git checkout develop
git pull origin develop
git checkout -b feature/gmail-auto-reply

# 2. Разработка
# ... пишите код ...
git add .
git commit -m "feat: Add Gmail auto-reply functionality"

# 3. Push и создание PR
git push origin feature/gmail-auto-reply
# На GitHub: Create PR: feature/gmail-auto-reply → develop

# 4. После CI проверок и approval → merge в develop
# → Автоматический деплой в Staging

# 5. Тестирование на staging
# Проверьте функциональность на staging окружении

# 6. Готовы к production? Создайте PR: develop → main
# → После approval → автодеплой в Production
```

### Исправление бага

```bash
# От develop для обычных багов
git checkout develop
git checkout -b fix/email-validation

# От main для critical hotfix
git checkout main
git checkout -b hotfix/security-vulnerability
```

### Именование веток

```
feature/*  - Новая функциональность
fix/*      - Исправление бага
hotfix/*   - Критическое исправление в production
refactor/* - Рефакторинг кода
docs/*     - Обновление документации
test/*     - Добавление тестов
chore/*    - Обновление зависимостей, конфигурации
```

---

## Мониторинг

### Grafana (Staging)

```bash
URL: http://<staging-vm-ip>:3000
Login: admin
Password: admin (поменяйте!)

Dashboards:
- Backend Performance
- Celery Tasks
- PostgreSQL Metrics
- Redis Metrics
```

### Flower (Celery monitoring)

```bash
Staging: http://<staging-vm-ip>:5555
Production: http://<production-vm-ip>:5555
```

### Logs

```bash
# SSH в VM
ssh -i ~/.ssh/oracle_key ubuntu@<vm-ip>

# Backend logs
cd ~/Mail-Agent/backend
docker compose logs -f app

# Celery logs
docker compose logs -f celery-worker

# All services
docker compose logs -f
```

### Health Checks

```bash
# Backend
curl http://<vm-ip>:8000/health

# Database connection
curl http://<vm-ip>:8000/health/db

# Redis connection
curl http://<vm-ip>:8000/health/redis
```

---

## Troubleshooting

### Deployment Failed

**1. Проверьте logs на VM:**
```bash
ssh -i ~/.ssh/oracle_key ubuntu@<vm-ip>
cd ~/Mail-Agent/backend
docker compose ps
docker compose logs
```

**2. Проверьте secrets в GitHub:**
```bash
GitHub → Settings → Secrets and variables → Actions
# Убедитесь, что все секреты заполнены
```

**3. Проверьте health:**
```bash
curl http://<vm-ip>:8000/health
```

### Database Connection Issues

**1. Проверьте connection string:**
```bash
# На VM
cd ~/Mail-Agent/backend
cat .env | grep DATABASE_URL
```

**2. Проверьте Autonomous DB:**
```bash
Oracle Console → Autonomous Database → [ваша БД]
# Status должен быть: Available
```

**3. Проверьте Alembic миграции:**
```bash
ssh ubuntu@<vm-ip>
cd ~/Mail-Agent/backend
docker compose exec app /app/.venv/bin/alembic current
```

### SSL Certificate Issues

```bash
# На production VM
sudo certbot renew --dry-run
sudo certbot certificates
sudo systemctl status certbot.timer
```

### Docker Issues

```bash
# Restart services
docker compose down
docker compose up -d

# Clean up
docker system prune -a
docker volume prune

# Check resources
docker stats
```

### GitHub Actions не запускаются

**1. Проверьте workflow syntax:**
```bash
# Локально установите act для тестирования
brew install act
act -l
```

**2. Проверьте permissions:**
```bash
GitHub → Settings → Actions → General
→ Workflow permissions: Read and write permissions
```

---

## Backup и Restore

### Создание бэкапа

```bash
# На VM
bash ~/Mail-Agent/backend/scripts/backup-database.sh staging

# Автоматизация через cron
crontab -e
# Добавьте:
0 2 * * * /home/ubuntu/Mail-Agent/backend/scripts/backup-database.sh staging
```

### Restore из бэкапа

```bash
# 1. Остановите приложение
docker compose down

# 2. Restore database
gunzip < ~/backups/database/mailagent_staging_20250114_020000.sql.gz | \
  docker exec -i $(docker ps -qf "name=db") psql -U mailagent -d mailagent

# 3. Запустите приложение
docker compose up -d
```

---

## Масштабирование

### Увеличение ресурсов VM

```bash
Oracle Console → Compute → Instances → [ваша VM] → Edit
# Можно увеличить OCPU и RAM в пределах Always Free
```

### Горизонтальное масштабирование

```bash
# Добавить больше Celery workers
docker compose up -d --scale celery-worker=4
```

---

## Полезные Команды

```bash
# Check running containers
docker compose ps

# View logs
docker compose logs -f

# Restart specific service
docker compose restart app

# Update code and redeploy
cd ~/Mail-Agent
git pull origin main
cd backend
docker compose down
docker compose up -d --build

# Check disk usage
df -h
docker system df

# Monitor resources
htop
docker stats
```

---

## Поддержка

- GitHub Issues: https://github.com/1987-Dmytro/Mail-Agent/issues
- Oracle Cloud Docs: https://docs.oracle.com/en-us/iaas/
- Vercel Docs: https://vercel.com/docs

---

**Создано: Winston, System Architect 🏗️**
