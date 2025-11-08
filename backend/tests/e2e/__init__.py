"""End-to-End (E2E) tests with REAL external APIs.

These tests verify complete integration with real external services:
- Gmail API (real account required)
- Gemini API (real API key required)
- Telegram API (real bot token required)

E2E tests are OPTIONAL and skipped by default in CI/CD.
Run them manually before releases to verify real API integration.

To run E2E tests:
    1. Configure environment variables (see tests/e2e/README.md)
    2. Run: pytest tests/e2e/ -v -m e2e

Note: These tests will:
- Make real API calls (cost money for Gemini)
- Create/delete real Gmail labels
- Send real Telegram messages
- Require valid credentials
"""
