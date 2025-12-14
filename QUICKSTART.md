# ⚡ Quick Start Guide - Mail Agent CI/CD

Быстрый старт для развёртывания Mail Agent с бесплатной инфраструктурой.

---

## 🎯 Что вы получите

```
✅ Автоматический CI/CD pipeline
✅ Staging + Production окружения
✅ Бесплатный хостинг (Oracle Cloud + Vercel)
✅ Мониторинг (Prometheus + Grafana)
✅ Автоматические деплои при push
✅ Стоимость: $0/месяц
```

---

## 🚀 Быстрый старт (30 минут)

### Шаг 1: Oracle Cloud Setup (10 мин)

1. **Регистрация:**
   - https://www.oracle.com/cloud/free/
   - Введите данные карты (не списывают деньги)

2. **Создайте 2 VM (Staging + Production):**
   ```
   Compute → Instances → Create Instance

   Настройки:
   - Shape: VM.Standard.A1.Flex (ARM)
   - OCPU: 2, Memory: 12 GB
   - Image: Ubuntu 22.04
   - Always Free: ✅
   ```

3. **Создайте 2 Autonomous DB:**
   ```
   Autonomous Database → Create

   Настройки:
   - Type: Transaction Processing
   - OCPU: 1, Storage: 20 GB
   - Always Free: ✅
   ```

4. **Настройте Security List:**
   ```
   Открыть порты: 22, 80, 443, 8000, 3000, 5555
   ```

5. **SSH в каждую VM и запустите:**
   ```bash
   wget https://raw.githubusercontent.com/1987-Dmytro/Mail-Agent/main/backend/scripts/setup-vm.sh
   bash setup-vm.sh staging  # или production
   ```

### Шаг 2: GitHub Secrets (5 мин)

```bash
GitHub → Settings → Secrets → Actions → New secret
```

**Минимальный набор:**
```yaml
STAGING_VM_IP: <IP вашей staging VM>
PRODUCTION_VM_IP: <IP вашей production VM>
ORACLE_SSH_PRIVATE_KEY: <ваш приватный SSH ключ>
STAGING_DATABASE_URL: <connection string от Oracle DB>
PRODUCTION_DATABASE_URL: <connection string от Oracle DB>
JWT_SECRET_KEY: $(openssl rand -base64 32)
ENCRYPTION_KEY: $(openssl rand -base64 32)
GMAIL_CLIENT_ID: <от Google Console>
GMAIL_CLIENT_SECRET: <от Google Console>
GEMINI_API_KEY: <от Google AI Studio>
GROQ_API_KEY: <от Groq>
```

### Шаг 3: Vercel Setup (5 мин)

1. **Import проекта:**
   - https://vercel.com
   - Import `Mail-Agent` repository
   - Root Directory: `frontend`

2. **Environment Variables:**
   ```bash
   Production:
   NEXT_PUBLIC_API_URL=http://<production-vm-ip>:8000

   Preview (develop):
   NEXT_PUBLIC_API_URL=http://<staging-vm-ip>:8000
   ```

3. **Git Integration:**
   ```
   Production Branch: main
   Preview Branch: develop
   ```

### Шаг 4: Первый деплой (5 мин)

```bash
# 1. Push workflows в develop
git checkout develop
git add .github/workflows backend/scripts
git commit -m "ci: Add CI/CD infrastructure"
git push origin develop

# → Автоматический деплой в Staging!

# 2. Проверьте staging
curl http://<staging-vm-ip>:8000/health

# 3. Деплой в production
git checkout main
git merge develop
git push origin main

# → Автоматический деплой в Production!
```

### Шаг 5: Branch Protection (5 мин)

```bash
GitHub → Settings → Branches → Add rule

Branch: main
☑ Require pull request reviews (1 approval)
☑ Require status checks:
  - backend-ci / test
  - frontend-ci / test
```

---

## 📦 Что создано

### GitHub Workflows
```
.github/workflows/
├── backend-ci.yml              # Backend тесты, линтинг
├── frontend-ci.yml             # Frontend тесты, линтинг
├── pr-checks.yml               # PR валидация
├── deploy-backend-staging.yml  # Staging деплой
├── deploy-backend-production.yml # Production деплой
└── deploy-frontend.yml         # Vercel уведомления
```

### Deployment Scripts
```
backend/scripts/
├── setup-vm.sh         # Настройка VM
├── setup-nginx.sh      # Nginx + SSL
├── backup-database.sh  # Бэкапы БД
└── docker-entrypoint.sh # Entrypoint (существующий)
```

### Документация
```
DEPLOYMENT.md   # Полное руководство
QUICKSTART.md   # Это файл
```

---

## 🔄 Git Workflow

```bash
# Разработка
git checkout develop
git checkout -b feature/new-feature
git commit -m "feat: Add feature"
git push origin feature/new-feature

# PR: feature → develop
# После merge → автодеплой в Staging

# Production release
# PR: develop → main
# После merge → автодеплой в Production
```

---

## 🎯 Access Points

### Staging
```
Backend:    http://<staging-vm-ip>:8000
API Docs:   http://<staging-vm-ip>:8000/docs
Frontend:   https://mail-agent-git-develop.vercel.app
Grafana:    http://<staging-vm-ip>:3000
Flower:     http://<staging-vm-ip>:5555
```

### Production
```
Backend:    https://api.yourdomain.com (после Nginx)
Frontend:   https://mail-agent.vercel.app
Flower:     http://<production-vm-ip>:5555
```

---

## 🐛 Troubleshooting

### Deployment не работает?

```bash
# 1. Проверьте secrets
GitHub → Settings → Secrets
# Все секреты заполнены?

# 2. Проверьте VM
ssh ubuntu@<vm-ip>
docker compose ps
docker compose logs

# 3. Проверьте health
curl http://<vm-ip>:8000/health
```

### CI тесты падают?

```bash
# Запустите локально
cd backend
DATABASE_URL="postgresql://..." pytest tests/

cd ../frontend
npm run test:run
```

---

## 📚 Дополнительная информация

- **Полная документация:** [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Architecture decisions:** [docs/architecture/](./docs/architecture/)
- **Sprint planning:** [docs/sprints/](./docs/sprints/)

---

## 💰 Стоимость

```
Oracle Cloud VMs (2x ARM):        $0 (Always Free)
Autonomous Databases (2x):        $0 (Always Free)
Vercel (Frontend):                $0 (Free tier)
GitHub Actions:                   $0 (2000 мин/мес бесплатно)
──────────────────────────────────────────────
Итого:                            $0/месяц 🎉
```

---

## ✅ Checklist

- [ ] Oracle Cloud VMs созданы
- [ ] Autonomous Databases настроены
- [ ] GitHub Secrets добавлены
- [ ] Vercel проект импортирован
- [ ] Branch Protection настроен
- [ ] Первый деплой в Staging успешен
- [ ] Первый деплой в Production успешен
- [ ] Nginx + SSL настроен (опционально)
- [ ] Мониторинг работает

---

**🎉 Готово! Теперь у вас полноценный CI/CD pipeline с нулевой стоимостью!**

Вопросы? Смотрите [DEPLOYMENT.md](./DEPLOYMENT.md) или создайте Issue.
