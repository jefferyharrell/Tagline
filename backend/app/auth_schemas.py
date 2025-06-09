"""
Authentication schemas for Tagline backend.

This module defines Pydantic models for request/response validation:
- Role schemas
- User schemas
- Authentication request/response schemas
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


# Role schemas
class RoleBase(BaseModel):
    name: str


class RoleCreate(RoleBase):
    description: Optional[str] = None


class RoleAssign(BaseModel):
    role_name: str


class RoleBulkAssign(BaseModel):
    role_names: List[str]


class Role(RoleBase):
    id: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    firstname: Optional[str] = None
    lastname: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None


class User(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    roles: List[Role]

    class Config:
        from_attributes = True


# Authentication schemas
class EmailVerifyRequest(BaseModel):
    email: EmailStr


class EmailVerifyResponse(BaseModel):
    eligible: bool


class StytchAuthRequest(BaseModel):
    token: str
    session_token: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user_roles: List[str]


# Eligible email schemas
class EligibleEmailBase(BaseModel):
    email: EmailStr


class EligibleEmailCreate(EligibleEmailBase):
    batch_id: Optional[str] = None


class EligibleEmailBulkCreate(BaseModel):
    emails: List[EmailStr]
    batch_id: Optional[str] = None


class EligibleEmail(EligibleEmailBase):
    id: str
    created_at: datetime
    batch_id: Optional[str]

    class Config:
        from_attributes = True


# User sync schemas for JSON-based operations
class UserSync(BaseModel):
    """User data for JSON-based sync operations"""
    email: EmailStr
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    roles: List[str] = []


class UserSyncList(BaseModel):
    """List of users for bulk sync operations"""
    users: List[UserSync]


# CSV Import/Export schemas (deprecated - keeping for transition)
class ImportSummary(BaseModel):
    """Summary of CSV import results"""

    users_added: int
    users_updated: int
    users_deactivated: int
    errors: List[str] = []
    warnings: List[str] = []


class UserChange(BaseModel):
    """Represents a change to a user during import"""

    email: EmailStr
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    roles: List[str] = []
    previous_roles: Optional[List[str]] = None  # For updates only


class ImportPreview(BaseModel):
    """Preview of changes that would be made by CSV import"""

    to_add: List[UserChange]
    to_update: List[UserChange]
    to_deactivate: List[UserChange]
    invalid_roles: List[str] = []
    validation_errors: List[str] = []
    total_changes: int = 0

    def __init__(self, **data):
        super().__init__(**data)
        self.total_changes = (
            len(self.to_add) + len(self.to_update) + len(self.to_deactivate)
        )
