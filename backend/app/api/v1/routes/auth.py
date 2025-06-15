"""
Authentication routes for Tagline backend.

This module provides API endpoints for:
- Email eligibility verification
- Stytch authentication
- User role management
- Eligible email management
- Development authentication bypass
- User CSV import/export
"""

import logging
from datetime import datetime
from typing import List

import stytch
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth_schemas as schemas
from app.auth_utils import create_access_token, get_current_admin, get_current_user
from app.config import Settings, get_settings
from app.db.database import get_db
from app.db.repositories.auth import (
    EligibleEmailRepository,
    RoleRepository,
    UserRepository,
)
from app.structlog_config import get_logger


def analyze_sync_changes(json_users: List[dict], existing_users: dict) -> dict:
    """
    Analyze what changes would be made by syncing user data.

    Args:
        json_users: Parsed user data from JSON
        existing_users: Dict of existing users keyed by email

    Returns:
        Dictionary with keys: to_add, to_update, to_deactivate
    """
    json_emails = {user["email"] for user in json_users}
    existing_emails = set(existing_users.keys())

    to_add = []
    to_update = []

    # Users in JSON data
    for json_user in json_users:
        email = json_user["email"]
        if email in existing_emails:
            existing = existing_users[email]
            # Check if anything changed
            if (
                json_user["firstname"] != (existing.firstname or "")
                or json_user["lastname"] != (existing.lastname or "")
                or set(json_user["roles"]) != {r.name for r in existing.roles}
            ):
                to_update.append(
                    {**json_user, "previous_roles": [r.name for r in existing.roles]}
                )
        else:
            to_add.append(json_user)

    # Users not in JSON data (to be deactivated)
    to_deactivate = []
    for email in existing_emails - json_emails:
        user = existing_users[email]
        # Don't deactivate users who are administrators and not in JSON data
        # This is a safety measure
        if not any(role.name == "administrator" for role in user.roles):
            to_deactivate.append(
                {
                    "email": email,
                    "firstname": user.firstname or "",
                    "lastname": user.lastname or "",
                    "roles": [r.name for r in user.roles],
                }
            )

    return {"to_add": to_add, "to_update": to_update, "to_deactivate": to_deactivate}


def ensure_administrator_role(user, email: str, db: Session, settings: Settings):
    """Ensure that the ADMINISTRATOR_EMAIL user has the administrator role."""
    if (
        settings.ADMINISTRATOR_EMAIL
        and email.lower() == settings.ADMINISTRATOR_EMAIL.lower()
    ):
        role_repo = RoleRepository(db)
        admin_role = role_repo.get_by_name("administrator")
        if admin_role and not any(role.name == "administrator" for role in user.roles):
            user.roles.append(admin_role)
            logger.info(
                "Assigned administrator role",
                operation="ensure_administrator_role",
                email=email
            )
            return True
    return False


def setup_user_with_default_roles(user, email: str, db: Session, settings: Settings):
    """
    Setup user with default member role and administrator role if applicable.
    Handles the commit and refresh automatically.
    """
    role_repo = RoleRepository(db)

    # Assign default member role if not already present
    member_role = role_repo.get_by_name("member")
    if member_role and not any(role.name == "member" for role in user.roles):
        user.roles.append(member_role)

    # Check if this user should have administrator role
    ensure_administrator_role(user, email, db, settings)

    # Commit changes
    db.commit()
    db.refresh(user)


def ensure_user_has_admin_role(user, email: str, db: Session, settings: Settings):
    """
    Ensure existing user has administrator role if they match ADMINISTRATOR_EMAIL.
    Handles the commit and refresh automatically.
    """
    role_changed = ensure_administrator_role(user, email, db, settings)
    if role_changed:
        db.commit()
        db.refresh(user)


logger = get_logger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

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
    logger.info(
        "Email verification request received",
        operation="verify_email",
        email=email_data.email
    )
    
    email_repo = EligibleEmailRepository(db)
    is_eligible = email_repo.is_eligible(email_data.email, settings)
    
    logger.info(
        "Email verification completed",
        operation="verify_email",
        email=email_data.email,
        eligible=is_eligible
    )
    
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
    logger.info(
        "Authenticating with token",
        operation="authenticate_user",
        token_prefix=auth_data.token[:10]
    )

    # Validate the Stytch token
    try:
        # Attempt to authenticate with magic links first
        try:
            auth_response = stytch_client.magic_links.authenticate(
                token=auth_data.token, session_token=auth_data.session_token
            )
            logger.info(
                "Magic link authentication successful",
                operation="authenticate_user",
                auth_method="magic_link"
            )
        except Exception as e:
            # If magic link auth fails, try OAuth tokens
            logger.info(
                "Magic link auth failed, trying OAuth",
                operation="authenticate_user",
                auth_method="oauth_fallback",
                error=str(e)
            )
            auth_response = stytch_client.oauth.authenticate(
                token=auth_data.token, session_token=auth_data.session_token
            )
            logger.info(
                "OAuth authentication successful",
                operation="authenticate_user",
                auth_method="oauth"
            )
    except Exception as e:
        logger.error(
            "Stytch authentication error",
            operation="authenticate_user",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # Get user info from Stytch
    try:
        user_data = stytch_client.users.get(user_id=auth_response.user_id)
        email = user_data.emails[0].email
    except Exception as e:
        logger.error(
            "Error retrieving user data from Stytch",
            operation="authenticate_user",
            error=str(e),
            error_type=type(e).__name__
        )
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
            logger.info(
                "Updating existing user with new Stytch ID",
                operation="authenticate_user",
                email=email
            )
            user.stytch_user_id = auth_response.user_id
            db.commit()
        else:
            # Create new user if doesn't exist by either method
            logger.info(
                "Creating new user",
                operation="authenticate_user",
                email=email
            )
            user = user_repo.create(email=email, stytch_user_id=auth_response.user_id)

            # Setup user with default roles
            if user:
                setup_user_with_default_roles(user, email, db, settings)

    # Ensure existing users get administrator role if they match ADMINISTRATOR_EMAIL
    ensure_user_has_admin_role(user, email, db, settings)

    # Create JWT with user info and roles
    user_roles = [role.name for role in user.roles]
    jwt_payload = {
        "user_id": user.id,
        "email": user.email,
        "firstname": user.firstname,
        "lastname": user.lastname,
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


@router.get("/me", response_model=schemas.User)
async def get_current_user_info(
    current_user: schemas.User = Depends(get_current_user),
):
    """Get current user information"""
    return current_user


@router.patch("/me", response_model=schemas.User)
async def update_current_user_info(
    user_update: schemas.UserUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user information"""
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user.id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user_update.firstname is not None:
        user.firstname = user_update.firstname  # type: ignore[assignment]
    if user_update.lastname is not None:
        user.lastname = user_update.lastname  # type: ignore[assignment]

    db.commit()
    db.refresh(user)

    return schemas.User.from_orm(user)


@router.post("/bypass", response_model=schemas.AuthResponse)
async def bypass_auth(
    email_data: schemas.EmailVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Authentication bypass endpoint for development and testing.

    This endpoint allows bypassing the normal authentication flow when:
    1. AUTH_BYPASS_ENABLED is set to 'true'
    2. The provided email is in the AUTH_BYPASS_EMAILS list
    """
    settings = get_settings()

    # Security check
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

        # Setup user with default roles
        if user:
            setup_user_with_default_roles(user, email_data.email, db, settings)

    # Ensure existing users get administrator role if they match ADMINISTRATOR_EMAIL
    ensure_user_has_admin_role(user, email_data.email, db, settings)

    # Create JWT with user info and roles
    user_roles = [role.name for role in user.roles]
    jwt_payload = {
        "user_id": user.id,
        "email": user.email,
        "firstname": user.firstname,
        "lastname": user.lastname,
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


# User management endpoints
@router.get("/users", response_model=dict)
@limiter.limit("30/minute")  # Allow frequent pagination requests
async def list_users(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin),  # Only admins can list users
):
    """
    List all users with pagination.

    Returns users with their roles and basic statistics.
    """
    user_repo = UserRepository(db)
    users, total = user_repo.list_all_users(limit=limit, offset=offset)

    # Calculate statistics
    active_count = sum(1 for user in users if user.is_active)
    admin_count = sum(
        1 for user in users if any(role.name == "administrator" for role in user.roles)
    )

    # Convert to response format
    user_list = []
    for user in users:
        user_list.append(
            {
                "id": user.id,
                "email": user.email,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "is_active": user.is_active,
                "roles": [role.name for role in user.roles],
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        )

    return {
        "users": user_list,
        "total": total,
        "statistics": {
            "total_users": total,
            "active_users": active_count,
            "administrators": admin_count,
        },
    }


@router.get("/users/export", response_model=List[schemas.UserSync])
@limiter.limit("10/minute")  # Export is expensive, limit more strictly
async def export_users(
    request: Request,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin),  # Only admins can export users
):
    """
    Export all users as JSON array.

    Returns a JSON array with user objects containing: email, firstname, lastname, roles
    """
    user_repo = UserRepository(db)
    users, _ = user_repo.list_all_users(limit=10000)  # Export all users

    # Convert to UserSync schema
    user_list = []
    for user in users:
        user_list.append(
            schemas.UserSync(
                email=user.email,
                firstname=user.firstname,
                lastname=user.lastname,
                roles=[role.name for role in user.roles],
            )
        )

    return user_list


@router.post("/users/sync", response_model=schemas.ImportSummary)
@limiter.limit("3/minute")  # Most sensitive operation - very restrictive
async def sync_users(
    request: Request,
    user_data: schemas.UserSyncList,
    db: Session = Depends(get_db),
    current_admin: schemas.User = Depends(
        get_current_admin
    ),  # Only admins can sync users
):
    """
    Sync users from JSON array, replacing entire user database.

    Accepts a JSON array with user objects containing: email, firstname, lastname, roles
    This will:
    - Add new users
    - Update existing users
    - Deactivate users not in the array (except administrators)
    """
    # Convert Pydantic models to dict format for existing logic
    json_users = []
    for user in user_data.users:
        json_users.append(
            {
                "email": user.email,
                "firstname": user.firstname or "",
                "lastname": user.lastname or "",
                "roles": user.roles,
            }
        )

    # Validate roles
    role_repo = RoleRepository(db)
    db_roles = {role.name for role in role_repo.get_all()}
    json_roles = set()
    for user in json_users:
        json_roles.update(user["roles"])

    invalid_roles = json_roles - db_roles

    if invalid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid roles found: {', '.join(sorted(invalid_roles))}",
        )

    # Safety check: ensure current admin won't lose access
    admin_email = current_admin.email
    admin_in_data = any(
        user["email"] == admin_email and "administrator" in user["roles"]
        for user in json_users
    )

    if not admin_in_data:
        # Add warning but don't block
        logger.warning(
            "Current admin not found with admin role in data",
            operation="sync_users",
            admin_email=admin_email
        )

    # Perform the sync
    user_repo = UserRepository(db)
    try:
        counts = user_repo.sync_users_from_csv(
            json_users
        )  # Method works with dict format

        # Add eligible emails for new users
        email_repo = EligibleEmailRepository(db)
        batch_id = f"json_sync_{datetime.utcnow().isoformat()}"
        for user in json_users:
            if user["roles"]:  # Only add if user has roles
                try:
                    # Check if email already exists before adding
                    if not email_repo.is_eligible(user["email"]):
                        email_repo.add(user["email"], batch_id=batch_id)
                except IntegrityError:
                    # Rollback this specific transaction and continue
                    db.rollback()
                    logger.warning(
                        "Email already exists in eligible_emails",
                        operation="sync_users",
                        email=user["email"]
                    )
                except Exception as e:
                    # Handle other potential errors
                    db.rollback()
                    logger.error(
                        "Error adding email to eligible_emails",
                        operation="sync_users",
                        email=user["email"],
                        error=str(e),
                        error_type=type(e).__name__
                    )

        warnings = []
        if not admin_in_data:
            warnings.append(
                f"Current admin {admin_email} was not in the data with administrator role"
            )

        return schemas.ImportSummary(
            users_added=counts["added"],
            users_updated=counts["updated"],
            users_deactivated=counts["deactivated"],
            errors=[],
            warnings=warnings,
        )

    except Exception as e:
        logger.error(
            "Error during sync",
            operation="sync_users",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during sync: {str(e)}",
        )


@router.post("/users/preview", response_model=schemas.ImportPreview)
@limiter.limit("15/minute")  # Preview operations for testing imports
async def preview_sync(
    request: Request,
    user_data: schemas.UserSyncList,
    db: Session = Depends(get_db),
    _: schemas.User = Depends(get_current_admin),  # Only admins can preview sync
):
    """
    Preview changes that would be made by syncing user data.

    This endpoint analyzes the JSON data and shows what would happen without making changes.
    """
    # Convert Pydantic models to dict format for existing logic
    json_users = []
    for user in user_data.users:
        json_users.append(
            {
                "email": user.email,
                "firstname": user.firstname or "",
                "lastname": user.lastname or "",
                "roles": user.roles,
            }
        )

    # Get existing users
    user_repo = UserRepository(db)
    existing_users = user_repo.get_all_users_dict()

    # Validate roles
    role_repo = RoleRepository(db)
    db_roles = {role.name for role in role_repo.get_all()}
    json_roles = set()
    for user in json_users:
        json_roles.update(user["roles"])

    invalid_roles = json_roles - db_roles

    # Analyze changes using existing utility
    changes = analyze_sync_changes(json_users, existing_users)

    # Convert to schema objects
    to_add = [schemas.UserChange(**user) for user in changes["to_add"]]
    to_update = [schemas.UserChange(**user) for user in changes["to_update"]]
    to_deactivate = [schemas.UserChange(**user) for user in changes["to_deactivate"]]

    validation_errors = []
    if invalid_roles:
        validation_errors.append(f"Invalid roles: {', '.join(sorted(invalid_roles))}")

    return schemas.ImportPreview(
        to_add=to_add,
        to_update=to_update,
        to_deactivate=to_deactivate,
        invalid_roles=list(invalid_roles),
        validation_errors=validation_errors,
    )
