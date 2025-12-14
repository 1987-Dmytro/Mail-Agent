"""Authentication and authorization endpoints for the API.

This module provides endpoints for user registration, login, session management,
and token verification.
"""

import uuid
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.responses import RedirectResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings
from app.core.encryption import (
    decrypt_token,
    encrypt_token,
)
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import (
    SessionResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services.database import DatabaseService
from app.utils.auth import (
    create_access_token,
    verify_token,
)
from app.utils.sanitization import (
    sanitize_email,
    sanitize_string,
    validate_password_strength,
)
from app.utils.oauth_state import (
    store_oauth_state,
    validate_oauth_state,
)

router = APIRouter()
security = HTTPBearer()


def get_db_service() -> DatabaseService:
    """Dependency injection for DatabaseService.

    Returns:
        DatabaseService: The database service singleton instance
    """
    from app.services.database import database_service
    return database_service


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_service: DatabaseService = Depends(get_db_service),
) -> User:
    """Get the current user ID from the token.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.

    Returns:
        User: The user extracted from the token.

    Raises:
        HTTPException: If the token is invalid or missing.
    """
    try:
        # JWT tokens are already safe (base64-encoded) and should NOT be sanitized
        # sanitize_string() would corrupt the token with html.escape()
        token = credentials.credentials

        user_id = verify_token(token)
        if user_id is None:
            logger.error("invalid_token", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify user exists in database
        user_id_int = int(user_id)
        user = await db_service.get_user(user_id_int)
        if user is None:
            logger.error("user_not_found", user_id=user_id_int)
            raise HTTPException(
                status_code=404,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Session:
    """Get the current session ID from the token.

    Args:
        credentials: The HTTP authorization credentials containing the JWT token.

    Returns:
        Session: The session extracted from the token.

    Raises:
        HTTPException: If the token is invalid or missing.
    """
    try:
        # Sanitize token
        token = sanitize_string(credentials.credentials)

        session_id = verify_token(token)
        if session_id is None:
            logger.error("session_id_not_found", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Sanitize session_id before using it
        session_id = sanitize_string(session_id)

        # Verify session exists in database
        session = await db_service.get_session(session_id)
        if session is None:
            logger.error("session_not_found", session_id=session_id)
            raise HTTPException(
                status_code=404,
                detail="Session not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return session
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
async def register_user(
    request: Request,
    user_data: UserCreate,
    db_service: DatabaseService = Depends(get_db_service),
):
    """Register a new user.

    Args:
        request: The FastAPI request object for rate limiting.
        user_data: User registration data

    Returns:
        UserResponse: The created user info
    """
    try:
        # Sanitize email
        sanitized_email = sanitize_email(user_data.email)

        # Extract and validate password
        password = user_data.password.get_secret_value()
        validate_password_strength(password)

        # Check if user exists
        if await db_service.get_user_by_email(sanitized_email):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user
        user = await db_service.create_user(email=sanitized_email, password=User.hash_password(password))

        # Create access token
        token = create_access_token(str(user.id))

        return UserResponse(id=user.id, email=user.email, token=token)
    except ValueError as ve:
        logger.error("user_registration_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["login"][0])
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    grant_type: str = Form(default="password"),
    db_service: DatabaseService = Depends(get_db_service),
):
    """Login a user.

    Args:
        request: The FastAPI request object for rate limiting.
        username: User's email
        password: User's password
        grant_type: Must be "password"

    Returns:
        TokenResponse: Access token information

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        # Sanitize inputs
        username = sanitize_string(username)
        password = sanitize_string(password)
        grant_type = sanitize_string(grant_type)

        # Verify grant type
        if grant_type != "password":
            raise HTTPException(
                status_code=400,
                detail="Unsupported grant type. Must be 'password'",
            )

        user = await db_service.get_user_by_email(username)
        if not user or not user.verify_password(password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(str(user.id))
        return TokenResponse(access_token=token.access_token, token_type="bearer", expires_at=token.expires_at)
    except ValueError as ve:
        logger.error("login_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/session", response_model=SessionResponse)
async def create_session(
    user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service),
):
    """Create a new chat session for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        SessionResponse: The session ID, name, and access token
    """
    try:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())

        # Create session in database
        session = await db_service.create_session(session_id, user.id)

        # Create access token for the session
        token = create_access_token(session_id)

        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user.id,
            name=session.name,
            expires_at=token.expires_at.isoformat(),
        )

        return SessionResponse(session_id=session_id, name=session.name, token=token)
    except ValueError as ve:
        logger.error("session_creation_validation_failed", error=str(ve), user_id=user.id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.patch("/session/{session_id}/name", response_model=SessionResponse)
async def update_session_name(
    session_id: str,
    name: str = Form(...),
    current_session: Session = Depends(get_current_session),
    db_service: DatabaseService = Depends(get_db_service),
):
    """Update a session's name.

    Args:
        session_id: The ID of the session to update
        name: The new name for the session
        current_session: The current session from auth

    Returns:
        SessionResponse: The updated session information
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)
        sanitized_name = sanitize_string(name)
        sanitized_current_session = sanitize_string(current_session.id)

        # Verify the session ID matches the authenticated session
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="Cannot modify other sessions")

        # Update the session name
        session = await db_service.update_session_name(sanitized_session_id, sanitized_name)

        # Create a new token (not strictly necessary but maintains consistency)
        token = create_access_token(sanitized_session_id)

        return SessionResponse(session_id=sanitized_session_id, name=session.name, token=token)
    except ValueError as ve:
        logger.error("session_update_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    current_session: Session = Depends(get_current_session),
    db_service: DatabaseService = Depends(get_db_service),
):
    """Delete a session for the authenticated user.

    Args:
        session_id: The ID of the session to delete
        current_session: The current session from auth

    Returns:
        None
    """
    try:
        # Sanitize inputs
        sanitized_session_id = sanitize_string(session_id)
        sanitized_current_session = sanitize_string(current_session.id)

        # Verify the session ID matches the authenticated session
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="Cannot delete other sessions")

        # Delete the session
        await db_service.delete_session(sanitized_session_id)

        logger.info("session_deleted", session_id=session_id, user_id=current_session.user_id)
    except ValueError as ve:
        logger.error("session_deletion_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.get("/sessions", response_model=List[SessionResponse])
async def get_user_sessions(
    user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_db_service),
):
    """Get all session IDs for the authenticated user.

    Args:
        user: The authenticated user

    Returns:
        List[SessionResponse]: List of session IDs
    """
    try:
        sessions = await db_service.get_user_sessions(user.id)
        return [
            SessionResponse(
                session_id=sanitize_string(session.id),
                name=sanitize_string(session.name),
                token=create_access_token(session.id),
            )
            for session in sessions
        ]
    except ValueError as ve:
        logger.error("get_sessions_validation_failed", user_id=user.id, error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


# Gmail OAuth Configuration
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels",
]


@router.get("/gmail/config")
async def get_gmail_oauth_config(request: Request):
    """Get Gmail OAuth 2.0 configuration.

    Returns the OAuth configuration needed by the frontend to initiate
    the Gmail authorization flow.

    Args:
        request: The FastAPI request object for rate limiting.

    Returns:
        dict: OAuth configuration including client_id, auth_url, and scopes

    Example:
        {
            "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=...&redirect_uri=...&...",
            "client_id": "your-client-id.apps.googleusercontent.com",
            "scopes": ["https://www.googleapis.com/auth/gmail.readonly", ...]
        }
    """
    # Build complete OAuth authorization URL with all required parameters
    # Generate state token for CSRF protection (same as /gmail/login)
    import secrets
    from urllib.parse import urlencode

    # Generate cryptographically secure state token
    state = secrets.token_urlsafe(32)

    # Store state in Redis for callback validation
    if not store_oauth_state(state):
        raise HTTPException(status_code=500, detail="Failed to generate OAuth state")

    params = {
        "client_id": settings.GMAIL_CLIENT_ID,
        "redirect_uri": settings.GMAIL_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,  # Include state in URL
    }

    auth_url_with_params = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

    logger.info("gmail_oauth_config_generated", state=state[:10] + "...", client_id=settings.GMAIL_CLIENT_ID[:20] + "...")

    return {
        "data": {
            "auth_url": auth_url_with_params,
            "client_id": settings.GMAIL_CLIENT_ID,
            "scopes": GMAIL_SCOPES,
            "state": state,  # Return state to frontend for validation (optional - frontend can extract from URL)
        }
    }


@router.post("/gmail/login")
async def gmail_login(request: Request):
    """Initiate Gmail OAuth 2.0 flow.

    Returns the authorization URL that the user should be redirected to
    for granting Gmail access permissions.

    Args:
        request: The FastAPI request object for rate limiting.

    Returns:
        dict: Authorization URL and success status

    Example:
        {
            "success": true,
            "data": {
                "authorization_url": "https://accounts.google.com/o/oauth2/auth?..."
            }
        }
    """
    try:
        # Create OAuth flow with client configuration
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": settings.GMAIL_CLIENT_ID,
                    "client_secret": settings.GMAIL_CLIENT_SECRET,
                    "redirect_uris": [settings.GMAIL_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=GMAIL_SCOPES,
        )

        flow.redirect_uri = settings.GMAIL_REDIRECT_URI

        # Generate authorization URL with state (CSRF token)
        authorization_url, state = flow.authorization_url(
            access_type="offline",  # Request refresh token
            include_granted_scopes="true",  # Incremental authorization
            prompt="consent",  # Force consent screen to get refresh token
        )

        # Store state in Redis for callback validation
        if not store_oauth_state(state):
            raise HTTPException(status_code=500, detail="Failed to generate OAuth state")

        logger.info("gmail_oauth_initiated", state=state[:10] + "...", client_id=settings.GMAIL_CLIENT_ID[:20] + "...")

        return {"success": True, "data": {"authorization_url": authorization_url}}

    except Exception as e:
        logger.error("gmail_oauth_init_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initiate OAuth flow: {str(e)}")


@router.get("/gmail/callback")
async def gmail_callback(
    state: str,
    code: str | None = None,
    error: str | None = None,
    db_service: DatabaseService = Depends(get_db_service),
):
    """Handle Gmail OAuth 2.0 callback.

    Receives the authorization code from Google, exchanges it for tokens,
    encrypts and stores tokens in the database.

    Args:
        state: State parameter for CSRF protection
        code: Authorization code from Google OAuth (present on success)
        error: Error code from Google OAuth (present on failure)
        db_service: Database service injected via dependency injection

    Returns:
        dict: User ID and email with success status

    Raises:
        HTTPException: If state validation fails, code is invalid, or token exchange fails
    """
    try:
        # Check if OAuth provider returned an error
        if error:
            logger.warning("oauth_callback_error", error=error, state=state[:10] + "..." if state else "unknown")

            # Map common OAuth errors to user-friendly messages
            error_messages = {
                "access_denied": "You declined to grant Gmail permissions. Please try again and approve the requested permissions.",
                "invalid_scope": "Invalid permissions requested. Please contact support.",
                "server_error": "Google's authorization server encountered an error. Please try again.",
                "temporarily_unavailable": "Google's authorization service is temporarily unavailable. Please try again later.",
            }

            user_message = error_messages.get(error, f"Authorization failed: {error}")
            raise HTTPException(status_code=403, detail=user_message)

        # If no error, code must be present
        if not code:
            logger.error("oauth_callback_missing_code", state=state[:10] + "..." if state else "unknown")
            raise HTTPException(status_code=400, detail="Missing authorization code")

        # Continue with normal OAuth flow
        # Sanitize input parameters to prevent injection attacks
        from app.utils.sanitization import sanitize_oauth_parameter
        try:
            code = sanitize_oauth_parameter(code, "code")
            state = sanitize_oauth_parameter(state, "state")
        except ValueError as e:
            logger.warning("oauth_parameter_validation_failed", error=str(e))
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")

        # Validate state parameter (CSRF protection) using Redis
        if not validate_oauth_state(state):
            logger.error("oauth_state_validation_failed", state=state[:10] + "...")
            raise HTTPException(status_code=403, detail="Invalid state parameter - possible CSRF attack")

        # Create OAuth flow with same configuration
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": settings.GMAIL_CLIENT_ID,
                    "client_secret": settings.GMAIL_CLIENT_SECRET,
                    "redirect_uris": [settings.GMAIL_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=GMAIL_SCOPES,
        )

        flow.redirect_uri = settings.GMAIL_REDIRECT_URI

        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Extract tokens
        access_token = credentials.token
        refresh_token = credentials.refresh_token
        token_expiry = credentials.expiry

        # Get user's Gmail email address
        gmail_service = build("gmail", "v1", credentials=credentials)
        profile = gmail_service.users().getProfile(userId="me").execute()
        email = profile["emailAddress"]

        # Encrypt tokens
        encrypted_access_token = encrypt_token(access_token)
        encrypted_refresh_token = encrypt_token(refresh_token)

        # Check if user exists by email
        user = await db_service.get_user_by_email(email)

        if user:
            # Update existing user's tokens
            user.gmail_oauth_token = encrypted_access_token
            user.gmail_refresh_token = encrypted_refresh_token
            if hasattr(user, "token_expiry"):
                user.token_expiry = token_expiry
            await db_service.update_user(user)
            logger.info("gmail_oauth_tokens_updated", user_id=user.id, email=email)
        else:
            # Create new user with Gmail tokens
            user = await db_service.create_user(
                email=email,
                password=None,  # OAuth user, no password
                gmail_oauth_token=encrypted_access_token,
                gmail_refresh_token=encrypted_refresh_token,
            )
            logger.info("gmail_oauth_user_created", user_id=user.id, email=email)

        # Create JWT token for the user
        token = create_access_token(str(user.id))

        # Redirect to frontend with token as query parameter
        # Frontend will extract token and store it
        # IMPORTANT: URL-encode parameters to prevent token corruption from special characters
        from urllib.parse import quote
        frontend_callback_url = f"{settings.FRONTEND_URL}/onboarding?token={quote(token.access_token, safe='')}&email={quote(email, safe='')}"
        logger.info("gmail_oauth_success_redirect", user_id=user.id, email=email, redirect_url=settings.FRONTEND_URL)

        return RedirectResponse(url=frontend_callback_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("gmail_oauth_callback_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@router.get("/status")
async def auth_status(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db_service: DatabaseService = Depends(get_db_service),
):
    """Get authentication status and user info.

    Checks if the user is authenticated and returns user information
    including Gmail and Telegram connection status.

    This endpoint does NOT require authentication - it checks if a token is provided
    and returns the user status if valid, or authenticated=false if not.

    Args:
        credentials: Optional HTTP authorization credentials containing JWT token
        db_service: Database service for user lookups

    Returns:
        dict: Authentication status and user information

    Example (authenticated):
        {
            "authenticated": true,
            "user": {
                "id": 1,
                "email": "user@gmail.com",
                "gmail_connected": true,
                "telegram_connected": false
            }
        }

    Example (not authenticated):
        {
            "authenticated": false
        }
    """
    # If no credentials provided, return not authenticated
    if not credentials:
        return {"authenticated": False}

    try:
        # Sanitize and verify token
        token = sanitize_string(credentials.credentials)
        user_id = verify_token(token)

        if user_id is None:
            return {"authenticated": False}

        # Get user from database
        user_id_int = int(user_id)
        user = await db_service.get_user(user_id_int)

        if user is None:
            return {"authenticated": False}

        # Check if user has Gmail tokens
        gmail_connected = bool(user.gmail_oauth_token and user.gmail_refresh_token)

        # Check if user has Telegram linked
        telegram_connected = bool(user.telegram_id)

        return {
            "authenticated": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "gmail_connected": gmail_connected,
                "telegram_connected": telegram_connected,
                "onboarding_completed": user.onboarding_completed,
            },
        }
    except Exception as e:
        logger.error("auth_status_check_failed", error=str(e), exc_info=True)
        # Don't fail - just return not authenticated
        return {"authenticated": False}


@router.get("/gmail/status")
async def gmail_status(user: User = Depends(get_current_user)):
    """Get Gmail OAuth connection status for the authenticated user.

    Checks if the user has valid Gmail OAuth tokens configured and
    optionally verifies they work by making a test API call.

    Args:
        user: The authenticated user from JWT token

    Returns:
        dict: Connection status information

    Example:
        {
            "success": true,
            "data": {
                "connected": true,
                "email": "user@gmail.com",
                "token_valid": true,
                "last_sync": "2025-11-04T10:15:30Z"
            }
        }
    """
    try:
        # Check if user has Gmail tokens
        has_tokens = bool(user.gmail_oauth_token and user.gmail_refresh_token)

        if not has_tokens:
            return {
                "success": True,
                "data": {
                    "connected": False,
                    "email": None,
                    "token_valid": False,
                    "last_sync": None,
                },
            }

        # Check token expiry
        token_valid = True
        if hasattr(user, "token_expiry") and user.token_expiry:
            from datetime import datetime, timezone

            token_valid = user.token_expiry > datetime.now(timezone.utc)

        # Optionally verify token by making Gmail API call
        email = user.email
        try:
            # Decrypt access token and create credentials
            access_token = decrypt_token(user.gmail_oauth_token)
            credentials = Credentials(token=access_token)

            # Make test call to Gmail API
            gmail_service = build("gmail", "v1", credentials=credentials)
            profile = gmail_service.users().getProfile(userId="me").execute()
            email = profile.get("emailAddress", user.email)
            token_valid = True
        except Exception as e:
            # Token verification failed, but don't fail the whole request
            logger.warning("gmail_token_verification_failed", user_id=user.id, error=str(e))
            token_valid = False

        last_sync = user.updated_at.isoformat() if user.updated_at else None

        return {
            "success": True,
            "data": {
                "connected": has_tokens,
                "email": email,
                "token_valid": token_valid,
                "last_sync": last_sync,
            },
        }

    except Exception as e:
        logger.error("gmail_status_check_failed", user_id=user.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check Gmail status: {str(e)}")


@router.get("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_user),
):
    """Protected test endpoint for authentication verification.
    
    This endpoint is used by integration tests to verify that authentication
    is working correctly. Returns 401 if not authenticated, 200 if authenticated.
    
    Args:
        current_user: Authenticated user from JWT token
        
    Returns:
        dict: Success response with user info
        
    Example:
        GET /api/v1/protected
        Authorization: Bearer <jwt_token>
        
        Response:
        {
            "success": true,
            "message": "Access granted",
            "user_id": 1
        }
    """
    return {
        "success": True,
        "message": "Access granted",
        "user_id": current_user.id,
    }
