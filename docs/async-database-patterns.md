# Async-Only Database Patterns for Epic 4+

**Date:** 2025-11-11
**Applies To:** All Epic 4+ stories
**Reason:** Epic 3 Stories 3.8-3.10 had async/sync confusion causing test failures

---

## TL;DR

✅ **ALWAYS USE:**
```python
async with self.db_service.async_session() as session:
    result = await session.execute(select(Model).where(...))
    obj = result.scalar_one_or_none()
```

❌ **NEVER USE:**
```python
with Session(self.db_service.engine) as session:  # FORBIDDEN
    obj = session.get(Model, id)
```

---

## Problem from Epic 3

**Stories Affected:** 3.8, 3.9, 3.10

**Symptoms:**
```
sqlalchemy.ext.asyncio.exc.AsyncContextNotStarted:
Async session not started in proper context
```

**Root Cause:** Mixing sync `Session(engine)` pattern with async `async_session()` pattern

---

## Correct Patterns

### 1. Basic Query (SELECT)

```python
# backend/app/services/settings_service.py

class SettingsService:
    def __init__(self, db_service: DatabaseService):
        self.db = db_service

    async def get_settings(self, user_id: int) -> UserSettings | None:
        """Get user settings by user_id"""
        async with self.db.async_session() as session:
            result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            return result.scalar_one_or_none()
```

### 2. Insert (CREATE)

```python
async def create_settings(self, user_id: int) -> UserSettings:
    """Create new user settings with defaults"""
    async with self.db.async_session() as session:
        settings = UserSettings(
            user_id=user_id,
            batch_notifications_enabled=True,
            batch_time="18:00"
        )
        session.add(settings)
        await session.commit()
        await session.refresh(settings)  # Get ID and defaults
        return settings
```

### 3. Update (MODIFY)

```python
async def update_batch_time(self, user_id: int, batch_time: str):
    """Update notification batch time"""
    async with self.db.async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one()

        settings.batch_time = batch_time
        settings.updated_at = datetime.utcnow()

        await session.commit()
```

### 4. Delete (REMOVE)

```python
async def delete_folder(self, folder_id: int):
    """Delete folder category"""
    async with self.db.async_session() as session:
        result = await session.execute(
            select(FolderCategory).where(FolderCategory.id == folder_id)
        )
        folder = result.scalar_one()

        await session.delete(folder)
        await session.commit()
```

### 5. Count / Aggregate

```python
async def get_folder_count(self, user_id: int) -> int:
    """Count user's folder categories"""
    async with self.db.async_session() as session:
        result = await session.execute(
            select(func.count(FolderCategory.id))
            .where(FolderCategory.user_id == user_id)
        )
        return result.scalar_one()
```

### 6. Join Queries

```python
async def get_user_with_settings(self, user_id: int):
    """Get user with settings (join)"""
    async with self.db.async_session() as session:
        result = await session.execute(
            select(User, UserSettings)
            .join(UserSettings, User.id == UserSettings.user_id)
            .where(User.id == user_id)
        )
        return result.one()
```

### 7. Batch Operations

```python
async def create_default_folders(self, user_id: int):
    """Create multiple folders in one transaction"""
    defaults = [
        {"name": "Important", "keywords": "urgent, asap"},
        {"name": "Government", "keywords": "finanzamt, tax"},
        {"name": "Clients", "keywords": "client, customer"},
    ]

    async with self.db.async_session() as session:
        for default in defaults:
            folder = FolderCategory(
                user_id=user_id,
                is_default=True,
                **default
            )
            session.add(folder)

        await session.commit()  # One commit for all
```

---

## Anti-Patterns (DO NOT USE)

### ❌ Anti-Pattern 1: Sync Session

```python
# WRONG - DO NOT USE
with Session(self.db_service.engine) as session:
    settings = session.get(UserSettings, user_id)
```

**Why Wrong:** Sync Session incompatible with async engine

**Fix:**
```python
# CORRECT
async with self.db_service.async_session() as session:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
```

### ❌ Anti-Pattern 2: Missing await

```python
# WRONG - DO NOT USE
async with self.db.async_session() as session:
    result = session.execute(select(UserSettings))  # Missing await!
    settings = result.scalar_one()
```

**Why Wrong:** `session.execute()` is async, must be awaited

**Fix:**
```python
# CORRECT
async with self.db.async_session() as session:
    result = await session.execute(select(UserSettings))
    settings = result.scalar_one()
```

### ❌ Anti-Pattern 3: session.get() (Sync Method)

```python
# WRONG - DO NOT USE
async with self.db.async_session() as session:
    settings = session.get(UserSettings, user_id)  # Sync method!
```

**Why Wrong:** `session.get()` is sync method, not available in async session

**Fix:**
```python
# CORRECT
async with self.db.async_session() as session:
    result = await session.execute(
        select(UserSettings).where(UserSettings.id == user_id)
    )
    settings = result.scalar_one_or_none()
```

### ❌ Anti-Pattern 4: Missing commit

```python
# WRONG - DO NOT USE
async with self.db.async_session() as session:
    settings = UserSettings(user_id=user_id)
    session.add(settings)
    # Missing await session.commit()!
```

**Why Wrong:** Changes not persisted to database

**Fix:**
```python
# CORRECT
async with self.db.async_session() as session:
    settings = UserSettings(user_id=user_id)
    session.add(settings)
    await session.commit()
```

---

## Test Patterns

### Unit Test with Async DB

```python
# backend/tests/test_settings_service.py

import pytest
from app.services.settings_service import SettingsService
from app.core.database import DatabaseService

@pytest.mark.asyncio
async def test_create_settings():
    """Test settings creation"""
    db_service = DatabaseService()
    settings_service = SettingsService(db_service)

    # Create settings
    settings = await settings_service.create_settings(user_id=12345)

    assert settings.user_id == 12345
    assert settings.batch_time == "18:00"

    # Cleanup
    await settings_service.delete_settings(12345)
```

### Integration Test with Real DB

```python
# backend/tests/integration/test_settings_integration.py

@pytest.mark.asyncio
async def test_settings_persistence():
    """Test settings persist across sessions"""
    db_service = DatabaseService()
    settings_service = SettingsService(db_service)

    # Create in one session
    await settings_service.create_settings(user_id=12345)

    # Read in another session (simulates different request)
    settings = await settings_service.get_settings(user_id=12345)
    assert settings is not None
    assert settings.batch_time == "18:00"

    # Cleanup
    await settings_service.delete_settings(12345)
```

---

## Migration from Sync to Async

If you find sync code in Epic 1-3:

### Before (Sync Pattern)
```python
def get_user(self, user_id: int):
    with Session(self.engine) as session:
        return session.get(User, user_id)
```

### After (Async Pattern)
```python
async def get_user(self, user_id: int):
    async with self.db_service.async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
```

### Changes Required:
1. Function becomes `async def`
2. `Session(engine)` → `async_session()`
3. `session.get()` → `session.execute(select().where())`
4. Add `await` before `session.execute()`
5. `.scalar_one_or_none()` for single result

---

## Checklist for Code Review

Before marking story "review-ready":

- [ ] All database operations use `async with self.db.async_session()`
- [ ] No `Session(engine)` usage anywhere
- [ ] All `session.execute()` calls have `await`
- [ ] No `session.get()` usage (sync method)
- [ ] All `session.commit()` calls have `await`
- [ ] All `session.refresh()` calls have `await` (if used)
- [ ] Functions accessing DB are `async def`
- [ ] Test fixtures use async sessions

---

## DatabaseService Reference

**Location:** `backend/app/core/database.py`

**Correct Usage:**
```python
from app.core.database import DatabaseService

db_service = DatabaseService()

async with db_service.async_session() as session:
    # Your async database operations
    result = await session.execute(select(Model))
    await session.commit()
```

**Available Methods:**
- `async_session()` - Create async session context manager ✅
- `engine` - Async engine (for internal use only)

---

## FAQ

**Q: Can I use sync Session for simple queries?**
A: No. Epic 4+ requires async-only. Mixing causes test failures.

**Q: What if I need to run blocking code?**
A: Use `asyncio.to_thread()` to run blocking code in thread pool.

**Q: How do I debug async database code?**
A: Use `await session.execute(select().execution_options(echo=True))` to log SQL.

**Q: Can I reuse session across multiple functions?**
A: No. Create new session in each service method. Session lifecycle = function scope.

---

## References

- **Epic 3 Retrospective:** `docs/retrospectives/epic-3-retro-2025-11-11.md` (Challenge #2)
- **Story Template V2.1.0:** `docs/story-template-v2.1-epic3-learnings.md`
- **DatabaseService:** `backend/app/core/database.py`
- **SQLModel Docs:** https://sqlmodel.tiangolo.com/tutorial/async/
- **SQLAlchemy Async:** https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

---

**Document Version:** 1.0
**Last Updated:** 2025-11-11
**Enforced Starting:** Epic 4 Story 4.1
