"""
Authentication routes for Tagline backend.

This module provides API endpoints for:
- Email eligibility verification
- Stytch authentication
- User role management
- Eligible email management
- Development authentication bypass
"""

import logging
from typing import List

import stytch
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth_schemas as schemas
from app.auth_utils import create_access_token, get_current_admin, get_current_user
from app.config import Settings, get_settings
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
    email_data: schemas.EmailVerifyRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Check if an email is eligible for registration"""
    email_repo = EligibleEmailRepository(db)
    is_eligible = email_repo.is_eligible(email_data.email, settings)
    return {"eligible": is_eligible}


@router.post("/authenticate", response_model=schemas.AuthResponse)
async def authenticate_user(
    auth_data: schemas.StytchAuthRequest,
    db: Session = Depends(get_db),
    stytch_client=Depends(get_stytch_client),
    settings: Settings = Depends(get_settings),
):
    """Authenticate a user with a Stytch token"""
    # Log debugging info
    logger.info(f"Authenticating with token: {auth_data.token[:10]}...")

    # Validate the Stytch token
    try:
        # Attempt to authenticate with magic links first
        try:
            auth_response = stytch_client.magic_links.authenticate(
                token=auth_data.token, session_token=auth_data.session_token
            )
            logger.info("Magic link authentication successful")
        except Exception as e:
            # If magic link auth fails, try OAuth tokens
            logger.info(f"Magic link auth failed, trying OAuth: {str(e)}")
            auth_response = stytch_client.oauth.authenticate(
                token=auth_data.token, session_token=auth_data.session_token
            )
            logger.info("OAuth authentication successful")
    except Exception as e:
        logger.error(f"Stytch authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # Get user info from Stytch
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
    if not email_repo.is_eligible(email, settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not eligible for access",
        )

    # Check if user exists by Stytch ID or email
    user_repo = UserRepository(db)
    user = user_repo.get_by_stytch_id(auth_response.user_id)

    if not user:
        # Try to find by email in case we have a user but with different Stytch ID
        user = user_repo.get_by_email(email)

        if user:
            # Update existing user with new Stytch ID
            logger.info(f"Updating existing user {email} with new Stytch ID")
            user.stytch_user_id = auth_response.user_id
            db.commit()
        else:
            # Create new user if doesn't exist by either method
            logger.info(f"Creating new user with email {email}")
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


@router.post("/bypass", response_model=schemas.AuthResponse)
async def bypass_auth(
    email_data: schemas.EmailVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Development-only endpoint for authentication bypass.

    This endpoint allows bypassing the normal authentication flow for development
    and testing purposes. It is only available when:
    1. The ENV_MODE setting is not 'production'
    2. AUTH_BYPASS_ENABLED is set to 'true'
    3. The provided email is in the AUTH_BYPASS_EMAILS list
    """
    settings = get_settings()

    # Log debugging info
    logger.info(f"Auth bypass requested for: {email_data.email}")
    logger.info(f"ENV_MODE: {settings.ENV_MODE}")
    logger.info(f"AUTH_BYPASS_ENABLED: {settings.AUTH_BYPASS_ENABLED}")
    logger.info(f"AUTH_BYPASS_EMAILS: {settings.AUTH_BYPASS_EMAILS}")

    # Security checks
    if settings.ENV_MODE == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auth bypass is not available in production mode",
        )

    if settings.AUTH_BYPASS_ENABLED != "true":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auth bypass is not enabled",
        )

    if not settings.AUTH_BYPASS_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No bypass emails configured",
        )

    # Check if email is in the allowed list
    allowed_emails = [email.strip() for email in settings.AUTH_BYPASS_EMAILS.split(",")]
    if email_data.email not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not authorized for bypass",
        )

    # Get or create user
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email_data.email)

    if not user:
        # Check if email is eligible
        email_repo = EligibleEmailRepository(db)
        if not email_repo.is_eligible(email_data.email, settings):
            # Auto-add to eligible emails for development
            email_repo.add(email_data.email, "dev-bypass")

        # Create user
        user = user_repo.create(
            email=email_data.email, stytch_user_id=f"dev-{email_data.email}"
        )

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
        "session_token": "dev-session",  # Dummy session token for dev
    }

    # Create access token
    access_token = create_access_token(data=jwt_payload)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_roles": user_roles,
    }


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
