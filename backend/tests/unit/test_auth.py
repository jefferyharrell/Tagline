"""Unit tests for the authentication system."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.auth_models import Role, User
from app.auth_schemas import User as UserSchema
from app.auth_utils import create_access_token, decode_token, get_user_with_roles


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = MagicMock(spec=User)
    user.id = str(uuid.uuid4())
    user.email = "test@example.com"
    user.is_active = True
    user.stytch_user_id = "stytch_test_id"
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()

    # Create mock roles
    admin_role = MagicMock(spec=Role)
    admin_role.name = "administrator"
    admin_role.id = str(uuid.uuid4())

    member_role = MagicMock(spec=Role)
    member_role.name = "member"
    member_role.id = str(uuid.uuid4())

    # Set user roles
    user.roles = [admin_role, member_role]

    # Add role checking methods
    user.has_role.side_effect = lambda role_name: role_name in ["administrator", "member"]
    user.has_any_role.side_effect = lambda role_names: any(
        r in role_names for r in ["administrator", "member"]
    )
    user.has_all_roles.side_effect = lambda role_names: all(
        r in ["administrator", "member"] for r in role_names
    )

    return user


def test_create_access_token():
    """Test creating a JWT access token."""
    # Test data
    test_data = {"user_id": "test_user", "email": "test@example.com"}

    # Create token
    token = create_access_token(test_data)

    # Verify token is a string
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_token():
    """Test decoding a JWT access token."""
    # Test data
    test_data = {"user_id": "test_user", "email": "test@example.com"}

    # Create token
    token = create_access_token(test_data)

    # Decode token
    decoded = decode_token(token)

    # Verify decoded data
    assert decoded["user_id"] == test_data["user_id"]
    assert decoded["email"] == test_data["email"]


def test_decode_token_expired():
    """Test decoding an expired JWT token."""
    # Test data with negative expiration
    test_data = {"user_id": "test_user", "email": "test@example.com"}

    # Create token that expires immediately
    token = create_access_token(test_data, expires_delta=timedelta(seconds=-1))

    # Decode token should raise exception
    with pytest.raises(HTTPException) as excinfo:
        decode_token(token)

    # Verify exception
    assert excinfo.value.status_code == 401
    assert "expired" in excinfo.value.detail.lower()


def test_get_user_with_roles():
    """Test the role-based authorization factory."""
    # Create a factory for users with admin role
    admin_only = get_user_with_roles(["administrator"])

    # Create a factory for users with member role
    member_only = get_user_with_roles(["member"])

    # Create a factory for users with both roles
    both_roles = get_user_with_roles(["administrator", "member"], require_all=True)

    # Create a factory for users with either role
    either_role = get_user_with_roles(["administrator", "member"], require_all=False)

    # Create a factory for users with a non-existent role
    non_existent_role = get_user_with_roles(["non_existent"])

    # Create a mock user schema
    user_schema = MagicMock(spec=UserSchema)
    admin_role = MagicMock()
    admin_role.name = "administrator"
    member_role = MagicMock()
    member_role.name = "member"
    user_schema.roles = [admin_role, member_role]

    # Test the factories
    assert admin_only.__name__ == "authorized_user"
    assert member_only.__name__ == "authorized_user"
    assert both_roles.__name__ == "authorized_user"
    assert either_role.__name__ == "authorized_user"
    assert non_existent_role.__name__ == "authorized_user"
