"""Store-manager sign-in. Customers never sign in; only the /store API is protected.

One shared manager password (env SAIDIT_MANAGER_PASSWORD). Signing in sets an HttpOnly
session cookie, so page scripts can't read the token; sessions live in memory and expire.
Deliberately small: no user accounts, no roles beyond "manager".
"""
from __future__ import annotations

import os
import secrets
import time

from fastapi import HTTPException, Request, Response

MANAGER_PASSWORD = os.environ.get("SAIDIT_MANAGER_PASSWORD", "store123")
COOKIE = "saidit_manager"
SESSION_SECONDS = 12 * 60 * 60

_sessions: dict[str, float] = {}  # token -> expiry (unix time)


def check_password(password: str) -> bool:
    # constant-time compare so response timing doesn't leak how much of the password matched
    return secrets.compare_digest(password.encode(), MANAGER_PASSWORD.encode())


def start_session(response: Response) -> None:
    token = secrets.token_urlsafe(32)
    _sessions[token] = time.time() + SESSION_SECONDS
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict")


def end_session(request: Request, response: Response) -> None:
    _sessions.pop(request.cookies.get(COOKIE, ""), None)
    response.delete_cookie(COOKIE)


def is_manager(request: Request) -> bool:
    token = request.cookies.get(COOKIE)
    expiry = _sessions.get(token or "")
    if expiry is None:
        return False
    if expiry < time.time():
        _sessions.pop(token, None)
        return False
    return True


def require_manager(request: Request) -> None:
    """FastAPI dependency for every store-manager endpoint."""
    if not is_manager(request):
        raise HTTPException(401, "store manager sign-in required")
