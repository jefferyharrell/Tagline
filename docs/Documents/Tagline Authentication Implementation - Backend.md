---
tags:
  - tagline
  - authentication
  - implementation
date: 2025-05-16
author: Alpha
---

This document provides a comprehensive implementation guide for the Tagline authentication system backend, featuring a multi-role user model and integration with Stytch for magic link authentication.

## Data Models

### Role and User with Many-to-Many Relationship

```python
# models.py
from sqlalchemy import Column, String, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

# Many-to-many association table between users and roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
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
            {"name": "sustainer", "description": "Sustainer JLLA member"}
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
```

## Repository Pattern

```python
# repositories.py
from sqlalchemy.orm import Session
from . import models
from typing import List

class RoleRepository:
    def __init__(self, db: Session):
        self.db = db
        
    def get_by_name(self, name: str):
        return self.db.query(models.Role).filter(models.Role.name == name).first()
        
    def get_all(self):
        return self.db.query(models.Role).all()
        
    def create(self, name: str, description: str = None):
        role = models.Role(name=name, description=description)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

class UserRepository:
    def __init__(self, db: Session):
        self.db = db
        
    def get_by_email(self, email: str):
        return self.db.query(models.User).filter(models.User.email == email).first()
        
    def get_by_stytch_id(self, stytch_id: str):
        return self.db.query(models.User).filter(models.User.stytch_user_id == stytch_id).first()
    
    def create(self, email: str, stytch_user_id: str = None):
        user = models.User(email=email, stytch_user_id=stytch_user_id)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
        
    def update_stytch_id(self, email: str, stytch_user_id: str):
        user = self.get_by_email(email)
        if user:
            user.stytch_user_id = stytch_user_id
            self.db.commit()
            self.db.refresh(user)
        return user
    
    def add_role(self, user_id: str, role_name: str):
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
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
    
    def remove_role(self, user_id: str, role_name: str):
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return None
            
        role_repo = RoleRepository(self.db)
        role = role_repo.get_by_name(role_name)
        if not role:
            return None
            
        if role in user.roles:
            user.roles.remove(role)
            self.db.commit()
            self.db.refresh(user)
        return user
    
    def set_roles(self, user_id: str, role_names: List[str]):
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
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
        
    def is_eligible(self, email: str):
        return self.db.query(models.EligibleEmail).filter(models.EligibleEmail.email == email).first() is not None
        
    def add_email(self, email: str, batch_id: str = None):
        eligible_email = models.EligibleEmail(email=email, batch_id=batch_id)
        self.db.add(eligible_email)
        self.db.commit()
        self.db.refresh(eligible_email)
        return eligible_email
        
    def bulk_add(self, emails, batch_id: str = None):
        eligible_emails = [models.EligibleEmail(email=email, batch_id=batch_id) for email in emails]
        self.db.bulk_save_objects(eligible_emails)
        self.db.commit()
```

## Pydantic Models

```python
# schemas.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

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
        orm_mode = True

class User(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    roles: List[Role]
    
    class Config:
        orm_mode = True

class EmailVerifyRequest(BaseModel):
    email: EmailStr

class StytchAuthRequest(BaseModel):
    token: str

class EligibleEmailCreate(BaseModel):
    email: EmailStr
    batch_id: Optional[str] = None

class EligibleEmailBulkCreate(BaseModel):
    emails: List[EmailStr]
    batch_id: Optional[str] = None
```

## Authentication and Authorization Router

```python
# auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import jwt
from typing import List
from datetime import datetime, timedelta
from . import database, models, schemas, repositories, settings
import stytch

router = APIRouter()

# Get db session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create Stytch client
def get_stytch_client():
    return stytch.Client(
        project_id=settings.STYTCH_PROJECT_ID,
        secret=settings.STYTCH_SECRET,
        environment=settings.STYTCH_ENV
    )

# Create JWT token
def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

@router.post("/verify-email-eligibility")
async def verify_email_eligibility(email_data: schemas.EmailVerifyRequest, db: Session = Depends(get_db)):
    email_repo = repositories.EligibleEmailRepository(db)
    is_eligible = email_repo.is_eligible(email_data.email)
    return {"eligible": is_eligible}

@router.post("/authenticate")
async def authenticate_user(auth_data: schemas.StytchAuthRequest, 
                           db: Session = Depends(get_db), 
                           stytch_client = Depends(get_stytch_client)):
    # Validate the Stytch token
    try:
        auth_response = stytch_client.magic_links.authenticate(
            token=auth_data.token,
            session_duration_minutes=60 * 24 * 7  # 1 week
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    # Check if user exists, create if they don't
    user_repo = repositories.UserRepository(db)
    user = user_repo.get_by_stytch_id(auth_response.user_id)
    
    if not user:
        # Get user email from Stytch
        try:
            user_data = stytch_client.users.get(user_id=auth_response.user_id)
            email = user_data.emails[0].email
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving user data"
            )
        
        # Check if email is eligible
        email_repo = repositories.EligibleEmailRepository(db)
        if not email_repo.is_eligible(email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not authorized for access"
            )
        
        # Check if user with this email already exists
        existing_user = user_repo.get_by_email(email)
        if existing_user:
            # Update existing user with Stytch ID
            user = user_repo.update_stytch_id(email, auth_response.user_id)
        else:
            # Create new user
            user = user_repo.create(email=email, stytch_user_id=auth_response.user_id)
            
            # Assign default "member" role to new users
            role_repo = repositories.RoleRepository(db)
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
        "session_token": auth_response.session_token
    }
    
    # Use JWT utilities to create the token
    access_token = create_access_token(data=jwt_payload)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_roles": user_roles
    }
```

## Access Control Dependencies

```python
# dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from . import models, database, settings
from typing import List

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

def has_role(required_role: str):
    async def _has_role(current_user: models.User = Depends(get_current_user)):
        if not current_user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have the required role: {required_role}",
            )
        return current_user
    return _has_role

def has_any_role(required_roles: List[str]):
    async def _has_any_role(current_user: models.User = Depends(get_current_user)):
        if not current_user.has_any_role(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have any of the required roles: {', '.join(required_roles)}",
            )
        return current_user
    return _has_any_role

# Shortcut dependencies for common roles
get_current_admin = has_role("admin")
get_current_member = has_role("member")
```

## Role Management Endpoints

```python
# Role management endpoints
@router.post("/admin/roles", status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: schemas.RoleCreate, 
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_admin)
):
    role_repo = repositories.RoleRepository(db)
    return role_repo.create(role_data.name, role_data.description)

@router.get("/admin/roles")
async def list_roles(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_admin)
):
    role_repo = repositories.RoleRepository(db)
    return role_repo.get_all()

@router.post("/admin/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: str,
    role_data: schemas.RoleAssign,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_admin)
):
    user_repo = repositories.UserRepository(db)
    user = user_repo.add_role(user_id, role_data.role_name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User or role not found"
        )
    return {"message": f"Role {role_data.role_name} assigned to user successfully"}

@router.delete("/admin/users/{user_id}/roles/{role_name}")
async def remove_role_from_user(
    user_id: str,
    role_name: str,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_admin)
):
    user_repo = repositories.UserRepository(db)
    user = user_repo.remove_role(user_id, role_name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User or role not found"
        )
    return {"message": f"Role {role_name} removed from user successfully"}

@router.put("/admin/users/{user_id}/roles")
async def set_user_roles(
    user_id: str,
    role_data: schemas.RoleBulkAssign,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_admin)
):
    user_repo = repositories.UserRepository(db)
    user = user_repo.set_roles(user_id, role_data.role_names)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User roles updated successfully", "roles": [role.name for role in user.roles]}
```

## Eligible Email Management Endpoints

```python
# Admin endpoints for managing eligible emails
@router.post("/admin/eligible-emails", status_code=status.HTTP_201_CREATED)
async def add_eligible_email(
    email_data: schemas.EligibleEmailCreate, 
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_admin)
):
    email_repo = repositories.EligibleEmailRepository(db)
    return email_repo.add_email(email_data.email, email_data.batch_id)

@router.post("/admin/eligible-emails/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_add_eligible_emails(
    email_data: schemas.EligibleEmailBulkCreate, 
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_admin)
):
    email_repo = repositories.EligibleEmailRepository(db)
    email_repo.bulk_add(email_data.emails, email_data.batch_id)
    return {"message": f"Successfully added {len(email_data.emails)} eligible emails"}
```

## Alembic Migration Files

### Create initial migration

```python
# versions/xxx_create_user_and_role_tables.py
"""create user and role tables

Revision ID: xxx
Revises: 
Create Date: 2025-05-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = 'xxx'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('email', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('stytch_user_id', sa.String(), nullable=True, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now())
    )
    
    # Create association table
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role_id', sa.String(), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
    )
    
    # Create eligible_emails table
    op.create_table(
        'eligible_emails',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('email', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('batch_id', sa.String(), nullable=True)
    )


def downgrade():
    op.drop_table('user_roles')
    op.drop_table('eligible_emails')
    op.drop_table('users')
    op.drop_table('roles')
```

## Settings Module

```python
# settings.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database configuration
    DATABASE_URL: str
    
    # JWT settings
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    
    # Stytch configuration
    STYTCH_PROJECT_ID: str
    STYTCH_SECRET: str
    STYTCH_ENV: str = "test"  # "test" or "live"
    
    # API configuration
    API_KEY: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Integration with Main FastAPI App

```python
# main.py
from fastapi import FastAPI, Depends
from .auth_router import router as auth_router

app = FastAPI(title="Tagline API")

# Include authentication router
app.include_router(auth_router, prefix="/v1/auth", tags=["authentication"])

# Include other routers...
```

## Environment Variables Example

```
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tagline

# JWT Settings
JWT_SECRET=your-jwt-secret-key
JWT_ALGORITHM=HS256

# Stytch configuration
STYTCH_PROJECT_ID=project-test-xxxxx
STYTCH_SECRET=secret-test-xxxxx
STYTCH_ENV=test

# API Key
API_KEY=your-api-key
```

## Initialization and Seeding

```python
# init_db.py
from sqlalchemy.orm import Session
from . import models, database

def seed_default_roles(db: Session):
    """Seed the default roles"""
    models.Role.seed_default_roles(db)

def init_db():
    """Initialize the database with default data"""
    db = database.SessionLocal()
    try:
        seed_default_roles(db)
    finally:
        db.close()
```
