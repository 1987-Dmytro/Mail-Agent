# 🔐 Автоматизация GitHub Secrets

Это руководство покажет, как автоматически создать и загрузить все GitHub Secrets за несколько минут.

---

## 🚀 Быстрый старт (3 способа)

### Способ 1: Интерактивный Wizard (Рекомендуется)

```bash
# Запустите интерактивный wizard
bash scripts/setup-secrets-wizard.sh
```

Wizard проведёт вас через все шаги и автоматически загрузит secrets в GitHub.

---

### Способ 2: Генерация + Ручное заполнение

```bash
# 1. Сгенерируйте базовые secrets
bash scripts/generate-secrets.sh

# 2. Откройте файл и заполните оставшиеся значения
vim .env.secrets

# 3. Загрузите в GitHub
bash scripts/upload-secrets.sh

# 4. Удалите файл
rm .env.secrets
```

---

### Способ 3: Полностью вручную через GitHub UI

Следуйте инструкциям в [.github/SECRETS_TEMPLATE.md](../.github/SECRETS_TEMPLATE.md)

---

## 📋 Что было сделано автоматически

### ✅ Уже сгенерировано

Файл `.env.secrets` создан с:
- `JWT_SECRET_KEY` - автоматически сгенерирован
- `ENCRYPTION_KEY` - автоматически сгенерирован
- Шаблоны для остальных секретов

### 📝 Нужно заполнить вручную

Откройте `.env.secrets` и заполните:

```bash
# 1. Oracle Cloud VM IP адреса
STAGING_VM_IP=<IP из Oracle Console>
PRODUCTION_VM_IP=<IP из Oracle Console>

# 2. SSH ключ
ORACLE_SSH_PRIVATE_KEY=<cat ~/.ssh/oracle_key>

# 3. Database URLs
STAGING_DATABASE_URL=postgresql://...
PRODUCTION_DATABASE_URL=postgresql://...

# 4. Gmail OAuth
GMAIL_CLIENT_ID=<из Google Console>
GMAIL_CLIENT_SECRET=<из Google Console>

# 5. AI API Keys
GEMINI_API_KEY=<из Google AI Studio>
GROQ_API_KEY=<из Groq Console>
```

---

## 🛠️ Требования

### Для автоматической загрузки в GitHub:

```bash
# Установите GitHub CLI
brew install gh  # macOS
# или
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg  # Linux

# Аутентифицируйтесь
gh auth login
```

---

## 📚 Где получить значения

### 1. Oracle Cloud VM IP

```bash
Oracle Console → Compute → Instances → [ваша VM]
→ Скопируйте "Public IP Address"
```

### 2. SSH Private Key

```bash
# На вашей локальной машине
cat ~/.ssh/oracle_key

# Или если ключ в другом месте
cat ~/.ssh/id_rsa
```

### 3. Database Connection Strings

```bash
Oracle Console → Autonomous Database → [ваша БД]
→ DB Connection → Download Wallet
→ Откройте tnsnames.ora из скачанного wallet
→ Найдите строку с "_high"
→ Преобразуйте в PostgreSQL формат:

postgresql://admin:YOUR_PASSWORD@host:1522/database_name
```

### 4. Gmail OAuth

```bash
1. Google Cloud Console: https://console.cloud.google.com
2. Создайте проект (или выберите существующий)
3. APIs & Services → Credentials
4. Create Credentials → OAuth 2.0 Client ID
5. Application type: Web application
6. Authorized redirect URIs:
   - http://localhost:3000/auth/gmail/callback
   - https://yourdomain.com/auth/gmail/callback
7. Скопируйте Client ID и Client Secret
```

### 5. Gemini API Key

```bash
1. Google AI Studio: https://aistudio.google.com/app/apikey
2. Create API key
3. Скопируйте ключ

⚠️ Free tier: 60 requests/minute
```

### 6. Groq API Key

```bash
1. Groq Console: https://console.groq.com
2. Зарегистрируйтесь
3. API Keys → Create API Key
4. Скопируйте ключ

⚠️ Free tier: 14,400 requests/day
```

---

## ✅ Проверка

После загрузки secrets, проверьте на GitHub:

```bash
# Откройте в браузере
https://github.com/1987-Dmytro/Mail-Agent/settings/secrets/actions

# Или через CLI
gh secret list --repo 1987-Dmytro/Mail-Agent
```

Должны быть видны 13 secrets:
- ✅ STAGING_VM_IP
- ✅ PRODUCTION_VM_IP
- ✅ ORACLE_SSH_PRIVATE_KEY
- ✅ STAGING_DATABASE_URL
- ✅ PRODUCTION_DATABASE_URL
- ✅ JWT_SECRET_KEY
- ✅ ENCRYPTION_KEY
- ✅ GMAIL_CLIENT_ID
- ✅ GMAIL_CLIENT_SECRET
- ✅ GEMINI_API_KEY
- ✅ GROQ_API_KEY
- ✅ STAGING_API_URL
- ✅ PRODUCTION_API_URL

---

## 🔧 Troubleshooting

### "gh: command not found"

```bash
# Установите GitHub CLI
brew install gh  # macOS

# Или скачайте с
https://cli.github.com/
```

### "gh auth login failed"

```bash
# Попробуйте другой метод аутентификации
gh auth login --web
```

### "Secret already exists"

```bash
# GitHub CLI автоматически обновит существующие secrets
# Или удалите и создайте заново:
gh secret delete SECRET_NAME --repo 1987-Dmytro/Mail-Agent
```

### Проверить SSH ключ

```bash
# Убедитесь, что это ПРИВАТНЫЙ ключ (не .pub)
cat ~/.ssh/oracle_key | head -1
# Должно быть: -----BEGIN OPENSSH PRIVATE KEY-----

# Публичный ключ НЕ подходит!
```

---

## 🔒 Безопасность

### ⚠️ ВАЖНО!

1. **НИКОГДА не коммитьте `.env.secrets`**
   - Файл автоматически добавлен в `.gitignore`
   - Проверьте: `git status` не должен показывать `.env.secrets`

2. **Удалите файл после загрузки**
   ```bash
   rm .env.secrets
   ```

3. **Не делитесь ключами**
   - API ключи личные
   - SSH ключи личные
   - Database пароли секретные

4. **Регулярно ротируйте секреты**
   - JWT_SECRET_KEY - каждые 6 месяцев
   - API ключи - при подозрении на утечку
   - Database пароли - раз в год

---

## 📞 Поддержка

Возникли проблемы?

1. Проверьте [Troubleshooting](#troubleshooting) выше
2. Смотрите [DEPLOYMENT.md](../DEPLOYMENT.md)
3. Создайте Issue на GitHub

---

## 🎯 Следующие шаги

После настройки secrets:

1. ✅ Проверьте на GitHub
2. 🚀 Запустите первый деплой:
   ```bash
   git add .
   git commit -m "ci: Add CI/CD infrastructure"
   git push origin develop
   ```
3. 📊 Проверьте GitHub Actions
4. 🎉 Наслаждайтесь автоматическим деплоем!

---

**Создано автоматически генератором secrets** 🔐
