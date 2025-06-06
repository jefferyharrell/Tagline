# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Philosophy
- Be lazy: check if it exists before building it
- Prefer: npm install > custom implementation  
- When missing dependencies: suggest installation, don't rebuild
- Exception: when requirements are so specific that existing solutions don't fit

## Project Overview

Tagline is a web application for the Junior League of Los Angeles (JLLA) that organizes and manages their vast photo collection stored on Dropbox. The application uses a two-silo architecture inspired by StudioCentral:

1. **Content Silo**: Storage providers (Dropbox, filesystem) house the actual media files
2. **Metadata Silo**: PostgreSQL database stores metadata, thumbnails, and proxy images

**Current Status**: Several solid days away from MVP. Backend was recently rewritten (completed ~May 4, 2025) and frontend updated to communicate with new architecture. Initial demo was presented to stakeholders on April 30, 2025.

**Active Development Focus**:
- LibraryView component implementation and integration
- Component-based UI architecture with shadcn/ui
- Performance optimization of API response times
- Media browsing and navigation user experience

**Note that** right now backend is considered more developed than frontend. If backend does something one way and frontend does it differently, check with the human but lean toward making frontend conform to backend.

## Application Vision

- The purpose of the Tagline backend is to synthesize from the storage provider's object space, the Postgres database, and the S3-compatible internal object space for proxies and thumbnails a single unified _media space_ that represents media objects (backed by supported file types on the storage provider) and which can be browsed and searched using API calls. The structure of the media space exactly mirrors, and is dept in sync with, the file structure of the storage provider.

- The purpose of the Tagline frontend is to provide a user-friendly interface for browsing, searching and annotating the metadata of media in the media space.

## Repository Structure

The repository is organized into two main directories:

- **backend/**: FastAPI application with PostgreSQL and Redis
- **frontend/**: Next.js 15 application with Tailwind CSS

## Development Commands

### Initial Setup

```bash
# Frontend initial setup
cd frontend && just setup

# Start all services
cd .. && just up
```

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

# Show available commands
just help
```

### Backend Commands

```bash
# Navigate to backend directory first
cd backend

# Run full quality check (format, lint, test, pre-commit)
just all

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

# Start backend containers (auto-runs migrations)
just up

# Stop backend containers
just down

# Run database migrations
just migrate

# Create new migration
just makemigration "Description of change"

# Open PostgreSQL shell
just dbshell

# Clean Python cache files
just clean

# Rebuild containers from scratch
just rebuild

# View backend logs
just logs

# Open bash shell in backend container
just shell

# Install/sync Python dependencies
just pip-install
```

### Frontend Commands

```bash
# Navigate to frontend directory first
cd frontend

# Setup frontend dependencies
just setup

# Run format, lint, and type checks
just all

# Format code with prettier
just format

# Lint code with eslint
just lint

# Run TypeScript type checking
just type-check

# Run all checks (lint, type-check, build)
npm run check-all

# Run tests (currently commented out)
just test

# Run frontend development server
just run

# Start frontend container
just up

# Stop frontend container
just down

# Clean build artifacts and node_modules
just clean

# Rebuild containers from scratch
just rebuild

# View frontend logs
just logs

# Open shell in frontend container
just shell

# Update npm dependencies
just update-deps
```

## Architecture

### Backend (FastAPI)

- RESTful API with JWT-based authentication via Stytch
- Storage Provider abstraction supporting filesystem and Dropbox
- Media processing pipeline for images (JPEG, PNG, HEIC)
- PostgreSQL database with SQLAlchemy ORM
- Redis-based background task queue for media ingestion
- Full-text search using PostgreSQL's tsvector/tsquery

Key patterns:
- Repository Pattern for data access (app/db/repositories/)
- Protocol-based interfaces for storage providers
- Factory Pattern for media processors
- Dependency Injection via FastAPI Depends
- Domain models separate from database models

Key directories:
- `app/api/v1/routes/`: API endpoint handlers
- `app/db/repositories/`: Data access layer
- `app/media_processing/`: Image processing pipeline
- `app/storage_providers/`: Storage abstraction implementations
- `app/tasks/`: Background job definitions

### Frontend (Next.js)

- Next.js 15 with React 19 and TypeScript
- Tailwind CSS v4 for styling
- shadcn/ui component library for consistent UI
- Authentication via Stytch magic links
- LibraryView component for unified media browsing
- Responsive design with server and client components

Key patterns:
- React Hooks for state management
- Provider Pattern for authentication state
- Server Components for data loading
- Route Handlers in app directory structure
- Proxy API routes for backend communication
- Component composition with reusable UI components

Key directories:
- `src/app/`: Next.js app router pages
- `src/app/api/`: API route handlers
- `src/components/`: Reusable UI components (LibraryView, FolderList, ThumbnailGrid, PhotoThumbnail)
- `src/components/ui/`: shadcn/ui base components
- `src/lib/`: Utility functions and helpers
- `src/types/`: TypeScript type definitions

Key components:
- `LibraryView`: Main component for browsing folders and media
- `FolderList`: Displays folder navigation with natural sorting
- `ThumbnailGrid`: Responsive grid layout for photo thumbnails
- `PhotoThumbnail`: Individual photo display with status indicators
- `MediaModal`: Modal for photo viewing and details

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

- `GET /v1/media`: List all media objects with pagination and search
- `GET /v1/media/search`: Full-text search across media metadata
- `GET /v1/media/{id}`: Get specific media object metadata
- `PATCH /v1/media/{id}`: Update media object metadata
- `GET /v1/media/{id}/thumbnail`: Get the thumbnail image
- `GET /v1/media/{id}/proxy`: Stream the proxy file
- `GET /v1/media/{id}/data`: Stream the full media file
- `GET /v1/media/{id}/adjacent`: Get previous/next media objects
- `POST /v1/auth/authenticate`: Authenticate with Stytch
- `POST /v1/auth/bypass`: Developer authentication bypass
- `POST /v1/ingest`: Scan storage for new media files
- `GET /v1/tasks`: List background tasks
- `GET /v1/tasks/{id}`: Get task status
- `GET /v1/storage/browse`: Browse folders and files with auto-discovery
- `GET /v1/folders/{path}`: Get folder structure at path (folders only)
- `GET /v1/media/by-folder/{path}`: Get media objects in specific folder (non-recursive)

### Frontend

- `/api/auth/callback`: Stytch callback handler
- `/api/auth/dev-login`: Developer login bypass
- `/api/auth/check-email`: Email eligibility verification
- `/api/library`: Proxy for backend media endpoints
- `/api/library/search`: Proxy for backend search
- `/api/library/{id}`: Proxy for specific media object
- `/api/library/{id}/thumbnail`: Proxy for thumbnail
- `/api/library/{id}/proxy`: Proxy for proxy image
- `/api/library/{id}/adjacent`: Proxy for adjacent media
- `/api/ingest`: Proxy for ingest endpoint
- `/api/logs`: Centralized logging endpoint (proxies to backend)

## Frontend Logging System

Tagline includes a centralized logging system that sends frontend logs to the backend for debugging:

### Logger Usage

```typescript
import logger from '@/lib/logger';

// Debug logs (development only)
logger.debug('User navigated to gallery', 'LibraryView', { path: '/photos' });

// Info logs
logger.info('Image processed successfully', 'IngestHandler', { objectKey: 'photo.jpg' });

// Warning logs
logger.warn('API response slow', 'APIClient', { responseTime: 2500 });

// Error logs (sent immediately, no batching)
logger.error('Failed to load images', 'LibraryView', { error: err.message });
```

### Key Features

- **Smart Batching**: Groups up to 10 logs every 2 seconds for efficiency
- **Immediate Errors**: Error logs bypass batching and send immediately
- **Structured Metadata**: Includes component, URL, timestamp, session ID, extra context
- **Graceful Fallback**: Falls back to console.log if backend unavailable
- **Authentication**: Properly handles cookie-based auth via frontend API proxy
- **Configuration**: Enabled in development, can be enabled in production via localStorage

### Backend Output Format

Logs appear in backend stdout as:
```
[FRONTEND-ERROR] 2024-01-01T12:00:00Z LibraryView [/library/photos]: Failed to load images | error=Network timeout
```

### Configuration

- **Development**: Enabled by default
- **Production**: Enable via `localStorage.setItem('enableFrontendLogging', 'true')`
- **Manual Control**: `logger.setEnabled(true/false)` or `logger.isEnabled()`

## Environment Configuration

### Backend Variables

- `BACKEND_API_KEY`: For X-API-Key header authentication
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET`: Secret for JWT token signing
- `STYTCH_PROJECT_ID`, `STYTCH_SECRET`: Stytch authentication
- `STORAGE_PROVIDER`: "filesystem" or "dropbox"
- `AUTH_BYPASS_EMAILS`: Comma-separated list of emails for bypass
- `AUTH_BYPASS_ENABLED`: Enable/disable auth bypass
- `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`: For Dropbox API access
- `DROPBOX_REFRESH_TOKEN`: Long-lived token for Dropbox
- `REDIS_URL`: Redis connection for task queue
- `FILESYSTEM_BASE_PATH`: Base path when using filesystem storage

### Frontend Variables

- `NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN`: Stytch public token
- `NEXT_PUBLIC_APP_URL`: Application URL for redirects
- `BACKEND_URL`: Backend API URL
- `BACKEND_API_KEY`: API key for backend communication
- `NEXT_PUBLIC_AUTH_BYPASS_ENABLED`: Enable auth bypass in frontend
- `JWT_SECRET`: For verifying JWT tokens in middleware

## Testing

### Backend Testing

- Backend uses pytest for unit and end-to-end tests
- Test files are in backend/tests/unit and backend/tests/e2e
- Run unit tests with `just unit-tests` in the backend directory
- Run e2e tests with `just e2e-tests` in the backend directory
- Run all tests with `just test`
- Generate coverage report with `just coverage`

**Test Patterns**:
- Unit tests mock external dependencies (database, storage providers)
- E2E tests use real database with test fixtures
- Conftest provides shared fixtures and test utilities
- Tests follow AAA pattern (Arrange, Act, Assert)

### Frontend Testing

- Frontend tests are currently commented out in Justfile
- Test infrastructure exists but needs implementation
- Manual testing should be performed with Playwright:
   - navigate to `http://localhost:3000`
   - sign in as `test@example.com`
   - press the purple `Developer Login` button at the bottom of the sign in page

### API Testing and Authentication Bypass

For testing backend APIs directly without going through the frontend authentication flow:

1. **Get authentication bypass token**:
```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/v1/auth/bypass" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{"email": "test@example.com"}' | jq -r '.access_token')
```

2. **Use token in API calls**:
```bash
# Test media objects
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Key: dev-api-key-12345" \
     "http://localhost:8000/v1/media?limit=5"

# Test storage browse
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Key: dev-api-key-12345" \
     "http://localhost:8000/v1/storage/browse"
```

**Note**: Auth bypass only works when `AUTH_BYPASS_ENABLED=true` and the email is in `AUTH_BYPASS_EMAILS` environment variables.

## Docker Compose Setup

The application runs in Docker containers orchestrated with Docker Compose.

### Backend Services

- `postgres`: PostgreSQL 17 database with pgvector extension (port 5432)
- `redis`: Redis 7 for task queue (port 6379)
- `backend`: FastAPI application (port 8000)
- `ingest-orchestrator`: Single RQ worker for task orchestration
- `ingest-worker`: RQ workers for parallel processing (8 replicas)

### Frontend Services

- `frontend`: Next.js development server (port 3000)
- Uses named volumes for node_modules and .next cache
- Volume mounts for hot reloading

### Service Dependencies

- Backend depends on postgres and redis
- Workers depend on backend, postgres, and redis
- Frontend can run independently but requires backend for API

### Volumes

- `postgres_data`: Persistent database storage
- `frontend_node_modules`: Cached dependencies
- `frontend_next`: Build cache

## Development Preferences & Conventions

- Use `just` commands rather than direct docker-compose for consistency
- Backend follows Python best practices with type hints
- Frontend uses TypeScript and follows React best practices
- Prefer functional components and hooks over class components
- Use Tailwind utility classes for styling
- Keep components focused and compose them together
- Write tests for new functionality
- Use meaningful commit messages and create PRs for review

### Type Safety Best Practices

- Define shared types in `src/types/` directory to avoid duplication
- Always run `npm run check-all` in frontend before committing
- This command runs: lint, type-check, and build to catch all issues
- Never define the same interface in multiple files
- Use strict TypeScript settings to catch errors early

### Component Development Guidelines

- Use shadcn/ui components for consistent styling (Breadcrumb, Button, etc.)
- Implement proper loading states or avoid them if API responses are fast (<100ms)
- Follow existing patterns: FolderList for folders, ThumbnailGrid for photo layouts
- Support both regular clicks (modals) and cmd/ctrl+clicks (navigation) for photos
- Use natural sorting for folder names (alphanumeric with proper numeric ordering)
- Implement proper error handling with retry mechanisms
- Create component specifications in `docs/component_specs/` for complex components

### Current Component Architecture

The frontend uses a modular component approach centered around the LibraryView component:

**LibraryView** (`src/components/LibraryView.tsx`):
- Main component integrating folder and photo browsing
- Handles URL synchronization and navigation state
- Manages photo modal display
- Uses shadcn/ui Breadcrumb components for navigation
- No loading states (700ms API response considered fast enough)

**FolderList** (`src/components/FolderList.tsx`):
- Displays folders in a responsive grid
- Implements natural sorting for folder names
- Shows empty state when no folders present

**ThumbnailGrid** (`src/components/ThumbnailGrid.tsx`):
- Container component for photo thumbnail layout
- Responsive grid (1-6 columns based on screen size)
- Accepts children components for flexible content

**PhotoThumbnail** (`src/components/PhotoThumbnail.tsx`):
- Individual photo display with loading states
- Shows status-specific icons (pending, processing, completed, failed)
- Handles image loading and error states
- Uses Skeleton component during loading

**MediaModal** (`src/components/MediaModal.tsx`):
- Reusable modal for photo viewing
- Supports ESC key, backdrop click, and button close
- Generic container accepting any content as children

**Integration Points**:
- Library pages (`/library`, `/library/[...path]`) use LibraryView directly
- Component test pages available at `/components/*` for development
- All components follow TypeScript strict mode with proper interfaces

## Stakeholder Context

- Primary users are Junior League of Los Angeles members
- Photo organization and discovery are key use cases
- Demo-by-screenshot capability was important for initial stakeholder presentation
- Future demos and stakeholder feedback sessions are planned
- Focus on practical usability over complex features for MVP