"""Repository for managing authentication-related models."""

import logging
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_models import EligibleEmail, Role, User
from app.config import Settings

logger = logging.getLogger(__name__)


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> Optional[Role]:
        """Get a role by name"""
        return self.db.query(Role).filter(Role.name == name).first()

    def get_all(self) -> List[Role]:
        """Get all roles"""
        return self.db.query(Role).all()

    def create(self, name: str, description: Optional[str] = None) -> Role:
        """Create a new role"""
        role = Role(name=name, description=description)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_stytch_id(self, stytch_user_id: str) -> Optional[User]:
        """Get a user by Stytch user ID"""
        return self.db.query(User).filter(User.stytch_user_id == stytch_user_id).first()

    def create(self, email: str, stytch_user_id: Optional[str] = None) -> User:
        """Create a new user"""
        user = User(email=email, stytch_user_id=stytch_user_id)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def add_role(self, user_id: str, role_name: str) -> Optional[User]:
        """Add a role to a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        role_repo = RoleRepository(self.db)
        role = role_repo.get_by_name(role_name)
        if not role:
            return None

        user.roles.append(role)
        self.db.commit()
        self.db.refresh(user)
        return user

    def remove_role(self, user_id: str, role_name: str) -> Optional[User]:
        """Remove a role from a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        role_repo = RoleRepository(self.db)
        role = role_repo.get_by_name(role_name)
        if not role:
            return None

        user.roles.remove(role)
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_roles(self, user_id: str, role_names: List[str]) -> Optional[User]:
        """Set all roles for a user (replacing existing roles)"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        role_repo = RoleRepository(self.db)
        roles = [role_repo.get_by_name(name) for name in role_names]
        roles = [role for role in roles if role]  # Filter out None values

        user.roles = roles
        self.db.commit()
        self.db.refresh(user)
        return user


class EligibleEmailRepository:
    def __init__(self, db: Session):
        self.db = db

    def is_eligible(self, email: str, settings: Optional["Settings"] = None) -> bool:
        """Check if an email is eligible"""
        # If settings provided and email matches administrator email, always grant access
        if settings and settings.ADMINISTRATOR_EMAIL:
            if email.lower() == settings.ADMINISTRATOR_EMAIL.lower():
                return True

        # Check the database for eligible email
        return (
            self.db.query(EligibleEmail).filter(EligibleEmail.email == email).first()
            is not None
        )

    def add(self, email: str, batch_id: Optional[str] = None) -> EligibleEmail:
        """Add an eligible email"""
        eligible_email = EligibleEmail(email=email, batch_id=batch_id)
        self.db.add(eligible_email)
        self.db.commit()
        self.db.refresh(eligible_email)
        return eligible_email

    def bulk_add(self, emails: List[str], batch_id: Optional[str] = None) -> int:
        """Add multiple eligible emails at once"""
        count = 0
        for email in emails:
            try:
                self.add(email, batch_id)
                count += 1
            except IntegrityError:
                self.db.rollback()
                logger.warning(f"Email {email} already exists in eligible_emails")
        return count

    def remove(self, email: str) -> bool:
        """Remove an eligible email"""
        eligible_email = (
            self.db.query(EligibleEmail).filter(EligibleEmail.email == email).first()
        )
        if eligible_email:
            self.db.delete(eligible_email)
            self.db.commit()
            return True
        return False

    def get_all(self, limit: int = 100, offset: int = 0) -> List[EligibleEmail]:
        """Get all eligible emails with pagination"""
        return self.db.query(EligibleEmail).offset(offset).limit(limit).all()


# Import the centralized get_db from database module
