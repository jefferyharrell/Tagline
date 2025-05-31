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
