"""Tests for API authentication module."""

import pytest
from fastapi import HTTPException

from foxhole_stockpiles.api.auth import verify_auth
from foxhole_stockpiles.core.settings import APIAuthSettings


class TestVerifyAuth:
    """Test cases for verify_auth function."""

    def test_auth_disabled_allows_access(self) -> None:
        """Test that requests are allowed when auth is disabled.

        When auth_type is None, authentication should not be enforced.
        """
        settings = APIAuthSettings(auth_type=None, auth_token=None)

        # Should not raise exception
        verify_auth(settings, None)
        verify_auth(settings, "any-header")

    def test_basic_auth_success(self) -> None:
        """Test successful basic authentication."""
        settings = APIAuthSettings(auth_type="basic", auth_token="dXNlcjpwYXNz")

        # Should not raise exception
        verify_auth(settings, "Basic dXNlcjpwYXNz")

    def test_basic_auth_failure_wrong_token(self) -> None:
        """Test basic auth fails with wrong token."""
        settings = APIAuthSettings(auth_type="basic", auth_token="dXNlcjpwYXNz")

        with pytest.raises(HTTPException) as exc_info:
            verify_auth(settings, "Basic wrong-token")

        assert exc_info.value.status_code == 401
        assert "Invalid authentication credentials" in exc_info.value.detail

    def test_basic_auth_failure_missing_header(self) -> None:
        """Test basic auth fails when header is missing."""
        settings = APIAuthSettings(auth_type="basic", auth_token="dXNlcjpwYXNz")

        with pytest.raises(HTTPException) as exc_info:
            verify_auth(settings, None)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    def test_bearer_auth_success(self) -> None:
        """Test successful bearer authentication."""
        settings = APIAuthSettings(auth_type="bearer", auth_token="my-secret-token")

        # Should not raise exception
        verify_auth(settings, "Bearer my-secret-token")

    def test_bearer_auth_failure_wrong_token(self) -> None:
        """Test bearer auth fails with wrong token."""
        settings = APIAuthSettings(auth_type="bearer", auth_token="my-secret-token")

        with pytest.raises(HTTPException) as exc_info:
            verify_auth(settings, "Bearer wrong-token")

        assert exc_info.value.status_code == 401
        assert "Invalid authentication credentials" in exc_info.value.detail

    def test_bearer_auth_failure_missing_header(self) -> None:
        """Test bearer auth fails when header is missing."""
        settings = APIAuthSettings(auth_type="bearer", auth_token="my-secret-token")

        with pytest.raises(HTTPException) as exc_info:
            verify_auth(settings, None)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    def test_custom_header_auth_success(self) -> None:
        """Test successful custom header authentication."""
        settings = APIAuthSettings(auth_type="X-API-Key", auth_token="custom-token-123")

        # Should not raise exception
        verify_auth(settings, "custom-token-123")

    def test_custom_header_auth_failure_wrong_token(self) -> None:
        """Test custom header auth fails with wrong token."""
        settings = APIAuthSettings(auth_type="X-API-Key", auth_token="custom-token-123")

        with pytest.raises(HTTPException) as exc_info:
            verify_auth(settings, "wrong-token")

        assert exc_info.value.status_code == 401
        assert "Invalid authentication credentials" in exc_info.value.detail

    def test_custom_header_auth_failure_missing_header(self) -> None:
        """Test custom header auth fails when header is missing."""
        settings = APIAuthSettings(auth_type="X-API-Key", auth_token="custom-token-123")

        with pytest.raises(HTTPException) as exc_info:
            verify_auth(settings, None)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail


class TestAPIAuthSettings:
    """Test cases for APIAuthSettings validation."""

    def test_both_none_is_valid(self) -> None:
        """Test that both auth_type and auth_token being None is valid."""
        settings = APIAuthSettings(auth_type=None, auth_token=None)
        assert settings.auth_type is None
        assert settings.auth_token is None

    def test_both_set_is_valid(self) -> None:
        """Test that both auth_type and auth_token being set is valid."""
        settings = APIAuthSettings(auth_type="bearer", auth_token="token")
        assert settings.auth_type == "bearer"
        assert settings.auth_token == "token"

    def test_only_auth_type_raises_error(self) -> None:
        """Test that setting only auth_type raises validation error."""
        with pytest.raises(ValueError) as exc_info:
            APIAuthSettings(auth_type="bearer", auth_token=None)

        assert "auth_type and auth_token must both be set or both be None" in str(exc_info.value)

    def test_only_auth_token_raises_error(self) -> None:
        """Test that setting only auth_token raises validation error."""
        with pytest.raises(ValueError) as exc_info:
            APIAuthSettings(auth_type=None, auth_token="token")

        assert "auth_type and auth_token must both be set or both be None" in str(exc_info.value)
