"""
Authentication models for Tagline backend.

This module defines SQLAlchemy models for authentication and authorization:
- Role: User roles (admin, member, active, sustainer)
- User: User accounts with Stytch integration
- EligibleEmail: Whitelist of authorized email addresses
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models import Base

# Many-to-many association table between users and roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "role_id", String, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship with users
    users = relationship("User", secondary=user_roles, back_populates="roles")

    @classmethod
    def seed_default_roles(cls, session):
        """Seed the default roles if they don't exist"""
        default_roles = [
            {"name": "admin", "description": "Administrator with full access"},
            {"name": "member", "description": "Basic JLLA member"},
            {"name": "active", "description": "Active JLLA member"},
            {"name": "sustainer", "description": "Sustainer JLLA member"},
        ]

        for role_data in default_roles:
            role = session.query(Role).filter_by(name=role_data["name"]).first()
            if role is None:
                role = Role(**role_data)
                session.add(role)

        session.commit()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    firstname = Column(String(100), nullable=True)
    lastname = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    stytch_user_id = Column(String, unique=True, nullable=True)  # Stytch's user ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship with roles
    roles = relationship("Role", secondary=user_roles, back_populates="users")

    def has_role(self, role_name):
        """Check if the user has a specific role"""
        return any(role.name == role_name for role in self.roles)

    def has_any_role(self, role_names):
        """Check if the user has any of the specified roles"""
        return any(role.name in role_names for role in self.roles)

    def has_all_roles(self, role_names):
        """Check if the user has all of the specified roles"""
        user_role_names = {role.name for role in self.roles}
        return all(role_name in user_role_names for role_name in role_names)


class EligibleEmail(Base):
    __tablename__ = "eligible_emails"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    batch_id = Column(String, nullable=True)  # Optional field to track import batches
