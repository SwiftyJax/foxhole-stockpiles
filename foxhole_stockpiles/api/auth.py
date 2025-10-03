"""Authentication module for FastAPI endpoints."""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Header, HTTPException, status

from foxhole_stockpiles.core.settings import APIAuthSettings


def verify_auth(auth_settings: APIAuthSettings, auth_header: str | None) -> None:
    """Verify authentication based on configured auth method.

    Args:
        auth_settings (APIAuthSettings): Authentication configuration
        auth_header (str | None): Authorization header value from the request

    Raises:
        HTTPException: 401 if authentication fails or is missing when required
    """
    # If auth is not configured, allow access
    if auth_settings.auth_type is None:
        return

    # Auth is required but no header provided
    if auth_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate based on auth type
    expected_token = auth_settings.auth_token
    auth_type = auth_settings.auth_type

    match auth_type:
        case "basic":
            expected_header = f"Basic {expected_token}"
            if auth_header != expected_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Basic"},
                )
        case "bearer":
            expected_header = f"Bearer {expected_token}"
            if auth_header != expected_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        case _:
            # Custom header - auth_type is the header name, token is the value
            # In this case, the auth_header should just be the token value
            if auth_header != expected_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )


def create_auth_dependency(
    auth_settings: APIAuthSettings,
) -> Callable[[str | None], Coroutine[Any, Any, None]]:
    """Create a FastAPI dependency for authentication.

    Args:
        auth_settings (APIAuthSettings): Authentication configuration

    Returns:
        Callable[[str | None], Coroutine[Any, Any, None]]: FastAPI dependency function
    """

    async def auth_dependency(authorization: str | None = Header(default=None)) -> None:
        """FastAPI dependency that validates authentication.

        Args:
            authorization (str | None): Authorization header from the request

        Raises:
            HTTPException: 401 if authentication fails
        """
        verify_auth(auth_settings, authorization)

    return auth_dependency
