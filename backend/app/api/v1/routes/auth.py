"""
Authentication routes for Tagline backend.

This module provides API endpoints for:
- Email eligibility verification
- Stytch authentication
- User role management
- Eligible email management
"""

import logging
from typing import List

import stytch
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth_schemas as schemas
from app.auth_utils import create_access_token, get_current_admin, get_current_user
from app.config import get_settings
from app.db.repositories.auth import (
    EligibleEmailRepository,
    RoleRepository,
    UserRepository,
    get_db,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Stytch client initialization
def get_stytch_client():
    """Get a configured Stytch client"""
    settings = get_settings()
    return stytch.Client(
        project_id=settings.STYTCH_PROJECT_ID,
        secret=settings.STYTCH_SECRET,
        environment=settings.STYTCH_ENV,
    )


@router.post("/verify-email", response_model=schemas.EmailVerifyResponse)
async def verify_email(
    email_data: schemas.EmailVerifyRequest, db: Session = Depends(get_db)
):
    """Check if an email is eligible for registration"""
    email_repo = EligibleEmailRepository(db)
    is_eligible = email_repo.is_eligible(email_data.email)
    return {"eligible": is_eligible}


@router.post("/authenticate", response_model=schemas.AuthResponse)
async def authenticate_user(
    auth_data: schemas.StytchAuthRequest,
    db: Session = Depends(get_db),
    stytch_client=Depends(get_stytch_client),
):
    """Authenticate a user with a Stytch token"""
    # Validate the Stytch token
    try:
        auth_response = stytch_client.magic_links.authenticate(
            token=auth_data.token, session_token=auth_data.session_token
        )
    except Exception as e:
        logger.error(f"Stytch authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # Check if user exists, create if they don't
    user_repo = UserRepository(db)
    user = user_repo.get_by_stytch_id(auth_response.user_id)

    if not user:
        # Get user email from Stytch
        try:
            user_data = stytch_client.users.get(user_id=auth_response.user_id)
            email = user_data.emails[0].email
        except Exception as e:
            logger.error(f"Error retrieving user data from Stytch: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving user data",
            )

        # Check if email is eligible
        email_repo = EligibleEmailRepository(db)
        if not email_repo.is_eligible(email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not eligible for access",
            )

        # Create new user
        user = user_repo.create(email=email, stytch_user_id=auth_response.user_id)

        # Assign default member role
        if user:
            role_repo = RoleRepository(db)
            member_role = role_repo.get_by_name("member")
            if member_role:
                user.roles.append(member_role)
                db.commit()
                db.refresh(user)

    # Create JWT with user info and roles
    user_roles = [role.name for role in user.roles]
    jwt_payload = {
        "user_id": user.id,
        "email": user.email,
        "roles": user_roles,
        "session_token": auth_response.session_token,
    }

    # Use JWT utilities to create the token
    access_token = create_access_token(data=jwt_payload)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_roles": user_roles,
    }


@router.get("/me", response_model=schemas.User)
async def get_current_user_info(current_user: schemas.User = Depends(get_current_user)):
    """Get information about the current authenticated user"""
    return current_user


@router.post("/roles/assign", response_model=schemas.User)
async def assign_role(
    role_data: schemas.RoleAssign,
    user_id: str,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin),  # Only admins can assign roles
):
    """Assign a role to a user"""
    user_repo = UserRepository(db)
    user = user_repo.add_role(user_id, role_data.role_name)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User or role not found"
        )

    return schemas.User.from_orm(user)


@router.post("/roles/bulk-assign", response_model=schemas.User)
async def bulk_assign_roles(
    role_data: schemas.RoleBulkAssign,
    user_id: str,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin),  # Only admins can assign roles
):
    """Assign multiple roles to a user"""
    user_repo = UserRepository(db)
    user = user_repo.set_roles(user_id, role_data.role_names)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return schemas.User.from_orm(user)


@router.delete("/roles/{role_name}", response_model=schemas.User)
async def remove_role(
    role_name: str,
    user_id: str,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin),  # Only admins can remove roles
):
    """Remove a role from a user"""
    user_repo = UserRepository(db)
    user = user_repo.remove_role(user_id, role_name)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User or role not found"
        )

    return schemas.User.from_orm(user)


@router.get("/roles", response_model=List[schemas.Role])
async def get_all_roles(
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin),  # Only admins can list all roles
):
    """Get all available roles"""
    role_repo = RoleRepository(db)
    return role_repo.get_all()


@router.post("/eligible-emails", response_model=schemas.EligibleEmail)
async def add_eligible_email(
    email_data: schemas.EligibleEmailCreate,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin),  # Only admins can add eligible emails
):
    """Add an email to the eligible list"""
    email_repo = EligibleEmailRepository(db)
    return email_repo.add(email_data.email, email_data.batch_id)


@router.post("/eligible-emails/bulk", response_model=dict)
async def bulk_add_eligible_emails(
    email_data: schemas.EligibleEmailBulkCreate,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin),  # Only admins can add eligible emails
):
    """Add multiple emails to the eligible list"""
    email_repo = EligibleEmailRepository(db)
    count = email_repo.bulk_add(email_data.emails, email_data.batch_id)
    return {"message": f"Successfully added {count} eligible emails"}
