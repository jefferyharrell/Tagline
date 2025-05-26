# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tagline is a web application for the Junior League of Los Angeles (JLLA) that organizes and manages their vast photo collection stored on Dropbox. The application uses a two-silo architecture inspired by StudioCentral:

1. **Content Silo**: Storage providers (Dropbox, filesystem) house the actual media files
2. **Metadata Silo**: PostgreSQL database stores metadata, thumbnails, and proxy images

**Current Status**: Several solid days away from MVP. Backend was recently rewritten (completed ~May 4, 2025) and frontend updated to communicate with new architecture. Initial demo was presented to stakeholders on April 30, 2025.

**Active Development Focus**:
- Metadata detail view enhancements
- Data entry interface improvements
- Tagging and search functionality refinement

**Note that** right now backend is considered more developed than frontend. If backend does something one way and frontend does it differently, check with the human but lean toward making frontend conform to backend.

## Repository Structure

The repository is organized into two main directories:

- **backend/**: FastAPI application with PostgreSQL and Redis
- **frontend/**: Next.js 15 application with Tailwind CSS

## Development Commands

### Project-Wide Commands

```bash
# Start both backend and frontend
just up

# Stop both services
just down

# Down and up in sequence
just bounce

# Restart both services
just restart
```

### Backend Commands

```bash
# Navigate to backend directory first
cd backend

# Format code with isort and black
just format

# Lint code with ruff and pyright
just lint

# Run unit tests
just unit-tests

# Run end-to-end tests
just e2e-tests

# Run all tests
just test

# Generate test coverage report
just coverage

# Run backend locally with uvicorn
just run

# Start backend containers
just up

# Stop backend containers
just down

# Run database migrations
just migrate

# Create new migration
just makemigration "Description of change"

# Open PostgreSQL shell
just dbshell
```

### Frontend Commands

```bash
# Navigate to frontend directory first
cd frontend

# Setup frontend dependencies
just setup

# Format code with prettier
just format

# Lint code with eslint
just lint

# Run tests
just test

# Run frontend development server
just run

# Start frontend container
just up

# Stop frontend container
just down
```

## Architecture

### Backend (FastAPI)

- RESTful API with JWT-based authentication via Stytch
- Storage Provider abstraction supporting filesystem and Dropbox
- Media processing pipeline for images (JPEG, PNG, HEIC)
- PostgreSQL database with SQLAlchemy ORM
- Redis-based background task queue for media ingestion

Key patterns:
- Repository Pattern for data access
- Protocol-based interfaces for storage providers
- Factory Pattern for media processors
- Dependency Injection via FastAPI Depends

### Frontend (Next.js)

- Modern React application with Tailwind CSS
- Authentication via Stytch magic links
- Media gallery for browsing and organizing photos
- Responsive design with server and client components

Key patterns:
- React Hooks for state management
- Provider Pattern for authentication state
- Server Components for data loading
- Route Handlers in app directory structure

## Authentication System

Tagline uses two authentication methods:

1. **Production Authentication**:
   - Stytch magic links sent via email
   - JWT tokens stored in HTTP-only cookies
   - Role-based access control

2. **Development Authentication Bypass**:
   - Special endpoint for bypassing magic links during testing
   - Controlled by AUTH_BYPASS_ENABLED and AUTH_BYPASS_EMAILS
   - Available when AUTH_BYPASS_ENABLED is set to 'true'

Authentication Flow:
1. User enters email on login page
2. Email checked against eligible users list
3. Magic link sent via Stytch API
4. User clicks link in email
5. Token validated by backend
6. JWT token generated and returned
7. Frontend stores JWT in HTTP-only cookie

## Key API Endpoints

### Backend

- `GET /v1/media`: List all media objects with pagination
- `GET /v1/media/{id}`: Get specific media object metadata
- `PATCH /v1/media/{id}`: Update media object metadata
- `GET /v1/media/{id}/thumbnail`: Get the thumbnail image
- `GET /v1/media/{id}/proxy`: Stream the proxy file
- `GET /v1/media/{id}/data`: Stream the full media file
- `POST /v1/auth/authenticate`: Authenticate with Stytch
- `POST /v1/auth/bypass`: Developer authentication bypass
- `POST /v1/ingest`: Scan storage for new media files

### Frontend

- `/api/auth/callback`: Stytch callback handler
- `/api/auth/dev-login`: Developer login bypass
- `/api/auth/check-email`: Email eligibility verification

## Environment Configuration

### Backend Variables

- `BACKEND_API_KEY`: For X-API-Key header authentication
- `DATABASE_URL`: PostgreSQL connection string (using Neon managed Postgres)
- `JWT_SECRET`: Secret for JWT token signing
- `STYTCH_PROJECT_ID`, `STYTCH_SECRET`: Stytch authentication
- `STORAGE_PROVIDER`: "filesystem" or "dropbox"
- `AUTH_BYPASS_EMAILS`: Comma-separated list of emails for bypass
- `AUTH_BYPASS_ENABLED`: Enable/disable auth bypass

### Frontend Variables

- `NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN`: Stytch public token
- `NEXT_PUBLIC_APP_URL`: Application URL for redirects
- `BACKEND_URL`: Backend API URL
- `BACKEND_API_KEY`: API key for backend communication
- `NEXT_PUBLIC_AUTH_BYPASS_ENABLED`: Enable auth bypass in frontend

## Testing

- Backend uses pytest for unit and end-to-end tests
- Test files are in backend/tests/unit and backend/tests/e2e
- Run unit tests with `just unit-tests` in the backend directory
- Run e2e tests with `just e2e-tests` in the backend directory
- Generate coverage report with `just coverage`

**Known Issues**:
- Playwright parallel testing can cause capacity problems on local development (likely connection pooling related)
- Consider investigating connection pooling configuration if running into database connection issues during testing

## Docker Compose Setup

The application runs in Docker containers orchestrated with Docker Compose.

### Backend Services

- PostgreSQL database
- Redis for task queue
- FastAPI application
- Ingest orchestrator worker
- Ingest workers (configurable replicas)

### Frontend Services

- Next.js development server
- Volume mounts for hot reloading

## Development Preferences & Conventions

- Use `just` commands rather than direct docker-compose for consistency
- Backend follows Python best practices with type hints
- Frontend uses TypeScript and follows React best practices
- Prefer functional components and hooks over class components
- Use Tailwind utility classes for styling
- Keep components focused and compose them together
- Write tests for new functionality
- Use meaningful commit messages and create PRs for review

## Stakeholder Context

- Primary users are Junior League of Los Angeles members
- Photo organization and discovery are key use cases
- Demo-by-screenshot capability was important for initial stakeholder presentation
- Future demos and stakeholder feedback sessions are planned
- Focus on practical usability over complex features for MVP