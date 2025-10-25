"""Authentication module for FastAPI endpoints."""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Header, HTTPException, status

from foxhole_stockpiles.core.settings.sections.api import APIAuthSettings


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
    # Note: auth_type is guaranteed to be either 'basic' or 'bearer' at this point
    # due to validation in APIAuthSettings (FORWARD is rejected for API auth)
    expected_token = auth_settings.auth_token
    auth_type = auth_settings.auth_type

    if auth_type == "basic":
        expected_header = f"Basic {expected_token}"
        if auth_header != expected_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
    elif auth_type == "bearer":
        expected_header = f"Bearer {expected_token}"
        if auth_header != expected_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        # This should never happen due to APIAuthSettings validation
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid authentication configuration",
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

    async def auth_dependency(
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> None:
        """FastAPI dependency that validates authentication.

        Args:
            authorization (str | None): Authorization header from the request.
                FastAPI will automatically extract this from the HTTP Authorization header.

        Raises:
            HTTPException: 401 if authentication fails
        """
        verify_auth(auth_settings, authorization)

    return auth_dependency
