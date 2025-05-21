# Tagline: LLM Developer Guide

This document provides essential context for LLMs working with the Tagline project.

## Project Overview

Tagline is a web application for the Junior League of Los Angeles (JLLA) that organizes and manages their collection of photos stored on Dropbox. The application handles tagging, searching, and metadata management for media objects using a two-silo architecture:

1. **Content Silo**: Storage providers (Dropbox, filesystem) house the actual media files
2. **Metadata Silo**: PostgreSQL database stores metadata, thumbnails, and proxy images

## Architecture

### Backend (FastAPI)

The backend implements a RESTful API with these key components:

- **Storage Provider Abstraction**: Interface for different media sources (filesystem, Dropbox)
- **Media Processing**: Handles image processing and thumbnail generation
- **Authentication**: JWT-based with Stytch for magic link emails
- **Database**: PostgreSQL with SQLAlchemy ORM

### Frontend (Next.js)

The frontend provides:

- **Authentication**: Stytch integration for magic links
- **Media Gallery**: Displays and organizes media objects
- **Metadata Editor**: Interface for editing tags and descriptions
- **Search**: Searches media objects by metadata

## Authentication System

Tagline uses two authentication methods:

1. **Production Authentication**: 
   - Stytch magic links sent via email
   - JWT tokens stored in HTTP-only cookies
   - Role-based access control (member, admin, etc.)

2. **Development Authentication Bypass**:
   - Special endpoint for bypassing magic links during testing
   - Controlled by environment variables and whitelists
   - Only available in development mode

## Core Data Models

### MediaObject

```python
class MediaObject:
    id: UUID
    object_key: str  # Identifier in the storage provider
    metadata: dict   # Flexible JSON for tags, descriptions, etc.
    thumbnail: bytes # Small thumbnail image
    proxy: bytes     # Medium-sized proxy image
    created_at: datetime
    updated_at: datetime
```

### Storage Provider Protocol

```python
class StorageProviderBase(Protocol):
    def list_media_objects(...): ...
    def retrieve(object_key: str) -> bytes: ...
    def iter_object_bytes(object_key: str) -> Iterable[bytes]: ...
    # Additional methods...
```

## Key API Endpoints

### Backend

- `GET /v1/media`: List all media objects with pagination
- `GET /v1/media/{id}`: Get specific media object metadata
- `PATCH /v1/media/{id}`: Update media object metadata
- `GET /v1/media/{id}/data`: Stream the full media file
- `GET /v1/media/{id}/thumbnail`: Get the thumbnail image
- `POST /v1/auth/authenticate`: Authenticate with Stytch
- `POST /v1/auth/bypass`: Developer authentication bypass
- `POST /v1/ingest`: Scan storage for new media files

### Frontend 

- `/api/auth/callback`: Stytch callback handler
- `/api/auth/dev-login`: Developer login bypass
- `/api/auth/check-email`: Email eligibility verification

## Configuration System

### Backend Environment Variables

- `API_KEY`: For X-API-Key header authentication
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET`: Secret for JWT token signing
- `STYTCH_PROJECT_ID`, `STYTCH_SECRET`: Stytch authentication
- `STORAGE_PROVIDER`: "filesystem" or "dropbox"
- `ENV_MODE`: "production", "development", or "test"
- `AUTH_BYPASS_EMAILS`: Comma-separated list of emails for bypass
- `AUTH_BYPASS_ENABLED`: Enable/disable auth bypass

### Frontend Environment Variables

- `NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN`: Stytch public token
- `NEXT_PUBLIC_APP_URL`: Application URL for redirects
- `BACKEND_URL`: Backend API URL
- `BACKEND_API_KEY`: API key for backend communication
- `NEXT_PUBLIC_AUTH_BYPASS_ENABLED`: Enable auth bypass in frontend

## Development Patterns

### Backend

- **Repository Pattern**: Data access through repository classes
- **Protocol-based Interfaces**: Storage providers and auth strategies
- **Factory Pattern**: Media processors selected based on file type
- **Dependency Injection**: Services injected via FastAPI Depends

### Frontend

- **React Hooks**: Custom hooks for authentication, fetching, etc.
- **Provider Pattern**: Context providers for authentication state
- **Server Components**: Next.js server components for data loading
- **Route Handlers**: API routes in the app directory structure

## Authentication Flow 

### Regular Flow

1. User enters email on login page
2. Email checked against eligible users list
3. Magic link sent via Stytch API
4. User clicks link in email
5. Token validated by backend
6. JWT token generated and returned
7. Frontend stores JWT in HTTP-only cookie

### Development Bypass Flow

1. Environment variables set with AUTH_BYPASS_ENABLED=true
2. Developer clicks "Developer Login" button
3. Frontend sends email to backend bypass endpoint
4. Backend checks if email is in AUTH_BYPASS_EMAILS list
5. JWT token generated (skipping Stytch)
6. Token returned and stored in cookie

## Implementing New Features

When adding features to Tagline:

1. **Backend**: 
   - Add new routes in appropriate route files
   - Use dependency injection for services
   - Update schemas for new data structures
   - Use the repository pattern for data access

2. **Frontend**:
   - Add new pages in app directory
   - Use server components where appropriate
   - Create API routes for backend communication
   - Update UI components in corresponding directories

## Project Context

Tagline is developed for the Junior League of Los Angeles to manage approximately 1,500 photos. The application aims to provide:

1. Secure, role-based access for JLLA members
2. Efficient tagging and organization of images
3. Fast searching by metadata
4. User-friendly interface for non-technical users

Prior work includes a demo presented in April 2025, with ongoing development of the gallery and admin views planned for completion.
