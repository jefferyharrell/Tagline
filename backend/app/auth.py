"""
Authentication strategies for Tagline backend.

- AuthStrategy: Protocol for pluggable authentication
- APIKeyStrategy: Implements X-API-Key header check
- JWTStrategy: Stub for future JWT support
"""

import os
from typing import Protocol

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader


class AuthStrategy(Protocol):
    async def authenticate(self, api_key: str) -> dict: ...


class APIKeyStrategy:
    """
    Authenticates requests using the X-API-Key header and a shared secret.
    The API key is loaded from the environment at authentication time to support dynamic environments (e.g., testing).
    """

    def __init__(self, api_key_env: str = "BACKEND_API_KEY"):
        self.api_key_env = api_key_env

    async def authenticate(self, api_key: str) -> dict:
        """
        Validate the provided API key against the environment variable.
        Returns an empty dict if valid, raises HTTPException otherwise.
        """
        expected_key = os.getenv(self.api_key_env, "")
        if api_key == expected_key:
            return {}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "API key"},
        )


class JWTStrategy:
    """
    Stub for JWT-based authentication. Not yet implemented.
    """

    async def authenticate(self, api_key: str) -> dict:
        raise NotImplementedError("JWT authentication not implemented yet.")


# Set the default strategy here for easy switching
active_auth_strategy: AuthStrategy = APIKeyStrategy()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def get_current_user(api_key: str = Depends(api_key_header)):
    """
    FastAPI dependency for authenticating the current user.
    This ensures the X-API-Key header is documented in OpenAPI and passed to the strategy.
    """
    return await active_auth_strategy.authenticate(api_key)
