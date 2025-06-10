"""
Authentication utilities for Tagline backend.

This module provides utilities for JWT token creation and validation,
as well as dependencies for FastAPI route protection.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.auth_schemas import User as UserSchema
from app.config import get_settings
from app.db.database import get_db
from app.db.repositories.auth import UserRepository

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")


def create_access_token(
    data: dict, expires_delta: timedelta = timedelta(days=7)
) -> str:
    """
    Create a JWT access token with the provided data and expiration.

    Args:
        data: The data to encode in the token
        expires_delta: How long the token should be valid

    Returns:
        JWT token string
    """
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Dict:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        The decoded token payload

    Raises:
        HTTPException: If the token is invalid or expired
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme), db=Depends(get_db)
) -> UserSchema:
    """
    FastAPI dependency to get the current authenticated user.

    Args:
        token: JWT token from the Authorization header
        db: Database session

    Returns:
        The current user

    Raises:
        HTTPException: If authentication fails
    """
    payload = decode_token(token)
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserSchema.from_orm(user)


def get_user_with_roles(
    required_roles: Optional[List[str]] = None, require_all: bool = False
):
    """
    Factory for creating dependencies that require specific roles.

    Args:
        required_roles: List of role names required for access
        require_all: If True, user must have all roles; if False, any role is sufficient

    Returns:
        FastAPI dependency function
    """

    async def authorized_user(
        current_user: UserSchema = Depends(get_current_user),
    ) -> UserSchema:
        if required_roles is None:
            return current_user

        user_roles = [role.name for role in current_user.roles]

        if require_all:
            # User must have all required roles
            if not all(role in user_roles for role in required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
        else:
            # User must have at least one of the required roles
            if not any(role in user_roles for role in required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

        return current_user

    return authorized_user


# Common role-based dependencies
get_current_admin = get_user_with_roles(["administrator"])
get_current_member = get_user_with_roles(["member", "administrator"])
get_current_active = get_user_with_roles(["active", "administrator"])
