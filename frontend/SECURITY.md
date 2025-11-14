# Security Best Practices - Mail Agent Frontend

**Last Updated**: 2025-11-11
**Status**: MVP - Production Hardening Roadmap Defined

## Authentication & Token Management

### Current Implementation (MVP)

**Access Token Storage**: localStorage
**Refresh Token**: httpOnly cookies (backend-managed)
**Token Refresh**: Automatic via `/api/v1/auth/refresh` endpoint

#### How It Works

1. **Login Flow**:
   - User completes Gmail OAuth flow
   - Backend returns JWT access token in response body
   - Frontend stores token in `localStorage` with key `mail_agent_token`
   - Token automatically added to requests via Axios interceptor

2. **Token Refresh Flow** (Implemented in Story 4.1):
   - When API returns 401 Unauthorized:
     - Frontend calls `/api/v1/auth/refresh` with `withCredentials: true`
     - Backend validates httpOnly refresh token cookie
     - Backend returns new access token
     - Frontend updates localStorage with new token
     - Original request automatically retried

3. **Logout Flow**:
   - Frontend removes token from localStorage
   - Backend clears httpOnly refresh token cookie

### Security Considerations

#### Current Risks (Acceptable for MVP)

**⚠️ XSS Vulnerability**: Access tokens in localStorage are accessible to JavaScript
- **Risk Level**: Medium
- **Mitigation (Current)**:
  - TypeScript strict mode prevents common XSS vectors
  - React auto-escapes user input
  - Content Security Policy (CSP) headers enforced by Vercel
  - All dependencies scanned for vulnerabilities (\`npm audit\`)
- **Mitigation (Planned)**: Production hardening (see roadmap below)

#### Production Hardening Roadmap

**Target: Story 4.8 or Post-MVP**

Migrate access tokens to httpOnly cookies for enhanced XSS protection.

### Current Security Measures (Implemented)

✅ **HTTPS Enforced**: Vercel deployment auto-provides HTTPS
✅ **withCredentials**: Axios configured to send httpOnly cookies
✅ **No Hardcoded Secrets**: All credentials in \`.env.local\` (gitignored)
✅ **npm Audit**: 0 vulnerabilities in production dependencies
✅ **TypeScript Strict Mode**: Prevents type-related vulnerabilities
✅ **Token Expiration Checking**: \`isTokenExpired()\` helper in auth.ts
✅ **Automatic Token Refresh**: Implemented in api-client.ts interceptor
✅ **Error Handling**: Comprehensive try-catch blocks prevent information leakage

### Gmail OAuth 2.0 Security

**OAuth Flow**: Authorization Code Grant (RFC 6749)
**Implementation**: Story 4.2 - Gmail OAuth Connection Page
**Components**: `GmailConnect.tsx`, `useAuthStatus.ts`

#### OAuth Security Measures (Implemented)

✅ **CSRF Protection** (AC: 5)
- State parameter generated using `crypto.randomUUID()` (cryptographically secure)
- State stored in sessionStorage (temporary, per-tab isolation)
- State validated on callback before exchanging authorization code
- Invalid state rejects authentication attempt

✅ **Authorization Code Flow** (Industry Standard)
- No client secret exposed to frontend (only client_id, which is public)
- Authorization code can only be used once
- Code exchanged for token on backend (confidential client)

✅ **OAuth Redirect URI Validation**
- Redirect URI must match backend configuration exactly
- Mismatch rejects OAuth callback
- Production: HTTPS-only redirect URIs (Vercel automatic)

✅ **Connection Persistence** (AC: 6)
- Auth status checked on page load via `useAuthStatus()` hook
- JWT token validation via `/api/v1/auth/status` endpoint
- Invalid/expired tokens trigger re-authentication
- No OAuth replay attacks (state token cleared after use)

✅ **Error Handling**
- User denial: Actionable error message ("Permission denied")
- Invalid state: Security warning ("Security validation failed")
- Network errors: Retry with backoff (no sensitive info exposed)
- No error stack traces exposed to user

#### OAuth Security Checklist

**MUST NOT**:
- ❌ Expose OAuth client secret in frontend code
- ❌ Store state token persistently (use sessionStorage only)
- ❌ Skip state parameter validation
- ❌ Use HTTP in production (HTTPS enforced by Vercel)
- ❌ Hardcode redirect URIs (backend-configured)

**MUST**:
- ✅ Generate state with `crypto.randomUUID()` (not Math.random())
- ✅ Validate state on every callback
- ✅ Clear state token after successful authentication
- ✅ Use HTTPS for OAuth flow in production
- ✅ Match redirect URI exactly between frontend and backend

#### OAuth Scopes Requested

The application requests the following Gmail API scopes:

1. `https://www.googleapis.com/auth/gmail.readonly` - Read emails for classification
2. `https://www.googleapis.com/auth/gmail.modify` - Mark emails as read/unread
3. `https://www.googleapis.com/auth/gmail.send` - Send approved responses
4. `https://www.googleapis.com/auth/gmail.labels` - Manage Gmail labels for organization

**Principle of Least Privilege**: Only scopes required for functionality are requested.

#### OAuth Token Storage

**Access Token**: localStorage (MVP-acceptable per Story 4.1 review)
- XSS risk documented and accepted for MVP
- Production hardening roadmap includes migration to httpOnly cookies

**State Token**: sessionStorage (temporary)
- Automatically cleared after OAuth callback
- Not accessible across browser tabs (isolation)

### API Security

**CORS Configuration** (Backend Responsibility):
- Whitelist only trusted frontend domains in production
- Development: \`http://localhost:3000\`
- Production: Frontend domain (configured on backend)

### Dependency Security

\`\`\`bash
# Run security audit
npm audit

# Fix vulnerabilities
npm audit fix
\`\`\`

**Current Status**: ✅ 0 vulnerabilities (as of 2025-11-11)

---

**Note**: This document will be updated as security measures are enhanced.
