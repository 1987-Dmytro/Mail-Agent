# OAuth и Telegram Integration - Исправления

## Что было исправлено

### 1. TOKEN_KEY Mismatch (ROOT CAUSE)
- **Проблема:** `getToken()` искал `'mail_agent_token'`, но OAuth сохранял `'auth_token'`
- **Исправление:** Изменен TOKEN_KEY в `frontend/src/lib/auth.ts:6` на `'auth_token'`

### 2. Race Condition - Token Extraction
- **Проблема:** Токен извлекался асинхронно в useEffect, API запросы выполнялись до сохранения токена
- **Исправление:** Добавлено синхронное извлечение токена в `OnboardingWizard.tsx:69-78`

### 3. Backend Token Handling
- **Проблема 1:** URL encoding отсутствовал → токен портился в redirect URL
- **Исправление:** Добавлено `urllib.parse.quote()` в `auth.py:622`

- **Проблема 2:** `sanitize_string()` портил JWT токены через `html.escape()`
- **Исправление:** Убран `sanitize_string()` из обработки JWT в `auth.py:84`

### 4. Автоматическая Обработка 403 Ошибок
- **Проблема:** При невалидном токене пользователь видел ошибки без автоматического recovery
- **Исправление:**
  - `api-client.ts:136-155` - автоматическая очистка токена и перезагрузка при 403
  - `OnboardingWizard.tsx:345-356` - проверка токена при загрузке, автоматический возврат на Gmail

## Автоматическое Восстановление

Система теперь автоматически:

1. **При 403 ошибке:**
   - Удаляет невалидный токен из localStorage
   - Очищает onboarding progress
   - Перезагружает страницу → начинается с Step 1

2. **При загрузке onboarding:**
   - Проверяет наличие токена
   - Если на Step 3+ без токена → возвращает на Step 2 (Gmail)

3. **При OAuth redirect:**
   - Извлекает токен синхронно ДО любых API запросов
   - Сохраняет с правильным ключом `'auth_token'`
   - URL-encoded для защиты от спецсимволов

## Если все еще не работает

**В консоли браузера (F12) выполните:**

```javascript
// Полная очистка
localStorage.clear();
sessionStorage.clear();

// Перезагрузка на onboarding
window.location.href = 'http://localhost:3000/onboarding';
```

После этого пройдите onboarding с начала - все должно работать автоматически.

## Технические Детали

**Файлы изменены:**
- `frontend/src/lib/auth.ts` - TOKEN_KEY fix
- `frontend/src/lib/api-client.ts` - 403 auto-recovery
- `frontend/src/components/onboarding/OnboardingWizard.tsx` - синхронное извлечение токена + валидация
- `backend/app/api/v1/auth.py` - URL encoding + убран sanitize
- `backend/app/utils/sanitization.py` - исключения для JWT

**Порядок выполнения OAuth flow:**
1. User clicks "Connect Gmail"
2. Backend генерирует OAuth URL с state
3. Redirect to Google OAuth consent
4. Google redirect back → `/auth/gmail/callback`
5. Backend создает JWT token
6. Backend redirect → `/onboarding?token=XXX&email=YYY`
7. OnboardingWizard **синхронно** извлекает token из URL (до рендера)
8. Token сохраняется → `localStorage.setItem('auth_token', token)`
9. TelegramStep монтируется → axios находит токен → успех!

**Защита от race conditions:**
- Токен извлекается СИНХРОННО в теле компонента (не в useEffect)
- Происходит ДО любого рендеринга дочерних компонентов
- Гарантирует что token в localStorage до первого API вызова
