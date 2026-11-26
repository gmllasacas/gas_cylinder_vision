import time
import secrets
import threading
from typing import Dict, List
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.core.config import settings
from app.core.logging import logger

security = HTTPBasic()

# In-memory brute force protection tracking failed attempts per IP
_failed_attempts: Dict[str, List[float]] = {}
_lock = threading.Lock()
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 60.0

def reset_auth_rate_limiter():
    """Resets the in-memory failure tracker (useful for testing)."""
    with _lock:
        _failed_attempts.clear()

def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    with _lock:
        timestamps = _failed_attempts.get(client_ip, [])
        valid_timestamps = [t for t in timestamps if now - t < LOCKOUT_WINDOW_SECONDS]
        _failed_attempts[client_ip] = valid_timestamps
        if len(valid_timestamps) >= MAX_FAILED_ATTEMPTS:
            oldest = valid_timestamps[0]
            retry_after = int(max(1, LOCKOUT_WINDOW_SECONDS - (now - oldest)))
            logger.warning(
                f"Rate limit exceeded: Temporary lockout for IP {client_ip} "
                f"due to {len(valid_timestamps)} consecutive failed auth attempts."
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed authentication attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

def _record_failure(client_ip: str, username: str) -> None:
    now = time.time()
    with _lock:
        if client_ip not in _failed_attempts:
            _failed_attempts[client_ip] = []
        _failed_attempts[client_ip].append(now)
    logger.warning(f"Failed authentication attempt from IP: {client_ip} | Attempted User: {username}")

def _record_success(client_ip: str) -> None:
    with _lock:
        _failed_attempts.pop(client_ip, None)

def get_current_admin(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security)
) -> str:
    """Validates HTTP Basic Auth credentials against configured admin settings with rate limiting and audit logging."""
    client_ip = request.client.host if request.client else "unknown"

    # 1. Enforce rate limit before checking credentials
    _check_rate_limit(client_ip)

    # 2. Timing-safe credential comparison
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.admin_username.encode("utf-8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.admin_password.encode("utf-8")
    )

    if not (correct_username and correct_password):
        _record_failure(client_ip, credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Reset failure tracking on successful authentication
    _record_success(client_ip)
    return credentials.username

