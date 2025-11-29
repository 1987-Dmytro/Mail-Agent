# Test Fixing Guide - Mail Agent Backend

## 📊 Current Status (2025-01-29)

### ✅ Completed (17 tests fixed)
- **test_error_handling_integration.py**: 14/14 PASSED (commit `ea615ac`)
- **test_approval_history_integration.py**: 5/5 PASSED (commit `1836eb1`)

### 🔧 Database Fixed
- **Issue**: PostgreSQL catalog corruption (`pg_type_typname_nsp_index` constraint violations)
- **Solution**: Database recreated cleanly
- **Command used**:
```bash
PGPASSWORD=mailagent_dev_password_2024 psql -h localhost -U mailagent -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'mailagent' AND pid <> pg_backend_pid();"
PGPASSWORD=mailagent_dev_password_2024 psql -h localhost -U mailagent -d postgres -c "DROP DATABASE mailagent;"
PGPASSWORD=mailagent_dev_password_2024 psql -h localhost -U mailagent -d postgres -c "CREATE DATABASE mailagent;"
```

### 📋 Remaining Work (~19 tests)

**Integration tests (14 tests in 8 files):**
1. test_context_retrieval_integration.py - 2 tests (slow, uses real ChromaDB)
2. test_email_polling_integration.py - 2 tests
3. test_epic_3_workflow_integration.py - 2 tests
4. test_complete_system_e2e.py - 1 test
5. test_epic_1_complete.py - 1 test
6. test_epic_3_workflow_integration_e2e.py - 1 test
7. test_oauth_integration.py - 3 tests (might be outdated cache)
8. test_response_generation_integration.py - 1 test
9. test_telegram_linking_integration.py - 1 test

**Unit tests (5 tests in 1 file):**
10. test_email_indexing.py - 5 tests (async mock issues)

---

## 🔧 Common Fix Pattern: db_factory

### Problem
Tests calling `execute_action()` from workflow nodes fail with:
```
TypeError: execute_action() got an unexpected keyword argument 'db'
```

### Root Cause
`execute_action()` requires `db_factory` (async context manager factory), not `db` (AsyncSession).

### Solution Template

**Step 1**: Add import
```python
from contextlib import asynccontextmanager
```

**Step 2**: Create db_factory wrapper
```python
# In the test function, before calling execute_action:
@asynccontextmanager
async def mock_db_factory():
    """Context manager factory that yields the mock db."""
    yield mock_db
```

**Step 3**: Update function call
```python
# OLD (will fail):
result_state = await execute_action(
    state=state,
    db=mock_db,  # ❌ Wrong
    gmail_client=mock_gmail,
)

# NEW (correct):
result_state = await execute_action(
    state=state,
    db_factory=mock_db_factory,  # ✅ Correct
    gmail_client=mock_gmail,
)
```

---

## 🚀 Recommended Workflow

### 1. Run Only Failed Tests
```bash
cd backend
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
  uv run pytest --lf -v --tb=short
```

### 2. Work on One File at a Time
```bash
# Example: Fix test_email_polling_integration.py
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
  uv run pytest tests/integration/test_email_polling_integration.py -v --tb=short
```

### 3. Identify the Error Pattern
- **db_factory issue**: Look for `TypeError: execute_action() got an unexpected keyword argument 'db'`
- **Async mock issue**: Look for `RuntimeWarning: coroutine was never awaited`
- **Database corruption**: Look for `pg_type_typname_nsp_index` errors (recreate DB)

### 4. Apply the Fix
- Use the pattern above for db_factory issues
- For async mock issues: ensure all mocks that return coroutines use `AsyncMock`

### 5. Test the Fix
```bash
# Run just the fixed tests
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
  uv run pytest tests/integration/test_YOUR_FILE.py -v
```

### 6. Commit Immediately
```bash
git add tests/integration/test_YOUR_FILE.py
git commit -m "fix(tests): Fix YOUR_FILE tests with db_factory pattern

Fixed N failing tests by converting from db parameter to db_factory
async context manager pattern.

Root cause: execute_action() requires db_factory (async context manager)
instead of db (AsyncSession) parameter.

Test results: N passed

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## ⚡ Performance Notes

### Test Execution Times
- **Single file**: 3-5 seconds (fast unit tests)
- **Integration tests**: 30-60+ seconds each (use real services)
- **Full suite (541 tests)**: 6-10 minutes (NORMAL, don't worry)

### Why Tests Are Slow
1. **Real services**: Integration tests use real ChromaDB, embeddings, etc.
2. **Database operations**: Each test creates/cleans database state
3. **Sequential execution**: 541 tests run one by one

### pytest-xdist (Parallel) - DO NOT USE
❌ **Does NOT work** with current setup due to:
- Shared database causes race conditions
- PostgreSQL catalog corruption from concurrent table creation
- Would need per-worker databases to fix

### Speed Optimization Strategy
✅ **Use targeted testing**:
```bash
# Run only failed tests (fastest)
pytest --lf

# Run specific file
pytest tests/integration/test_SPECIFIC.py

# Run specific test
pytest tests/integration/test_FILE.py::TestClass::test_name
```

---

## 🛠️ Troubleshooting

### Issue: Database Corruption
**Symptoms**: `pg_type_typname_nsp_index` constraint violations

**Solution**: Recreate database (see commands at top)

### Issue: Tests Hang/Run Forever
**Symptoms**: Integration test runs for 3+ minutes

**Solution**:
- Kill the process: `pkill -9 pytest`
- These tests are just slow (ChromaDB, embeddings)
- Read the test file to understand the issue instead of running

### Issue: Stale Test Cache
**Symptoms**: `--lf` shows tests that now pass

**Solution**: Clear pytest cache
```bash
rm -rf .pytest_cache
pytest --lf  # Will rebuild cache
```

---

## 📝 Next Files to Fix (Priority Order)

### High Priority (db_factory pattern likely)
1. **test_email_polling_integration.py** (2 tests) - probable db_factory issue
2. **test_epic_3_workflow_integration.py** (2 tests) - probable db_factory issue

### Medium Priority (different issues)
3. **test_email_indexing.py** (5 tests) - async mock issues
4. **test_context_retrieval_integration.py** (2 tests) - slow, complex

### Low Priority (verify if actually failing)
5. **test_oauth_integration.py** (3 tests) - might be stale cache
6. **Other integration tests** - various issues

---

## 🎯 Success Metrics

**Current**: 522/541 passing (96.5%)
**Target**: 541/541 passing (100%)
**Remaining**: ~19 tests to fix

**Commits so far**:
- `ea615ac`: test_error_handling_integration.py (14 tests)
- `1836eb1`: test_approval_history_integration.py (3 tests)

---

## 💡 Tips

1. **Don't run full suite every time** - Use `--lf` or specific files
2. **Commit early, commit often** - After each file fix
3. **Use the same pattern** - Most failures are db_factory related
4. **Integration tests are slow** - This is normal, be patient
5. **Read the error message** - It usually tells you exactly what's wrong
6. **Check pytest cache** - `cat .pytest_cache/v/cache/lastfailed`

---

## 📚 References

- **db_factory pattern**: See commits `ea615ac` and `1836eb1`
- **Database recreation**: Commands in this document
- **Test structure**: Follow existing test patterns in fixed files

---

**Good luck! You've got this! 🚀**
