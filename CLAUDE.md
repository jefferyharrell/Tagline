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

**Current Status**: MVP functionality complete and actively being refined. Backend was rewritten (completed ~May 4, 2025) and frontend updated to communicate with new architecture. Initial demo was presented to stakeholders on April 30, 2025.

**Active Development Focus**:
- User management via CSV import/export (recently completed)
- Virtual scrolling for large datasets (1,700+ users)
- Database performance optimization with comprehensive indexing
- UI/UX refinements and sidebar organization

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

## User Management System

Tagline includes a comprehensive user management system designed for administrative control:

### CSV-Based User Import/Export
- **"CSV is Truth" Model**: Upload CSV completely replaces existing user and role state
- **Variable Column Format**: Fixed columns (firstname, lastname, email) + variable role columns
- **Download/Upload Workflow**: Export current roster → Edit in Excel/Google Sheets → Upload
- **Role Assignment**: Natural handling of roles like "sustaining member" without quote complexity

### Administrative Interface
- **Access Control**: Only users with "administrator" role can access `/admin/users`
- **Virtual Scrolling**: Handles 1,700+ users efficiently with react-virtuoso
- **Real-time Filtering**: Search by name/email with active/inactive status filters
- **Preview Changes**: Shows what will be added/updated/deactivated before applying
- **Import Summary**: Displays counts of members added, updated, deactivated

### Role System
- `administrator`: Full admin access to user management and system features
- `member`: Basic JLLA member with standard access
- `active`: Active member status
- `sustainer`: Sustaining member classification
- Empty roles = inactive/ex-member user

### Security Features
- Role validation against database before sync
- Administrator safety checks (won't deactivate current admin)
- Rate limiting on sensitive operations (3/min for sync, 10/min for export)
- Comprehensive audit logging

### Eligible Emails System
- **Whitelist Control**: `eligible_emails` table controls who can authenticate
- **Automatic Population**: CSV user sync automatically adds emails to eligible list
- **Just-in-Time Users**: Stytch creates user accounts on first login attempt
- **Administrator Bypass**: `ADMINISTRATOR_EMAIL` environment variable bypasses eligibility check
- **Batch Tracking**: Import operations tagged with batch_id for audit trail

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
- `GET /v1/events/ingest`: Server-sent events for real-time media processing updates
- `GET /v1/tasks`: List background tasks
- `GET /v1/tasks/{id}`: Get task status
- `GET /v1/storage/browse`: Browse folders and files with auto-discovery
- `GET /v1/folders/{path}`: Get folder structure at path (folders only)
- `GET /v1/media/by-folder/{path}`: Get media objects in specific folder (non-recursive)
- `GET /v1/diagnostics/health`: Detailed health check with timing and resource info
- `GET /v1/diagnostics/detailed`: Comprehensive system diagnostics and performance metrics

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
- `/api/events/ingest`: Server-sent events proxy for real-time updates
- `/api/logs`: Centralized logging endpoint (proxies to backend)
- `/api/admin/users`: User management endpoints (list, export, sync, preview)

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

## Real-time Updates System

Tagline includes Server-Sent Events (SSE) for real-time media processing updates:

### Architecture
- **SSE Endpoint**: `/api/events/ingest` streams processing events from backend
- **Frontend Integration**: `SSEProvider` context manages connections app-wide
- **Component Integration**: `LibraryView` subscribes to relevant events for current path
- **Event Filtering**: Only processes events relevant to current folder/path being viewed

### Event Types
- `queued`: Media file queued for processing (filtered out in UI)
- `started`: Processing started (filtered out in UI) 
- `complete`: Processing finished, thumbnail/proxy ready (displayed in UI)
- `failed`: Processing failed with error information

### Features
- **Automatic Reconnection**: Exponential backoff with max 5 attempts
- **Path Filtering**: Only shows events relevant to current directory
- **Authentication Aware**: Connects only when user is authenticated
- **Graceful Degradation**: UI works without SSE connection

### Usage
```typescript
// Components subscribe via SSEProvider context
const { subscribe } = useSSE();
useEffect(() => {
  const unsubscribe = subscribe((event: IngestEvent) => {
    // Handle real-time thumbnail updates
    handleMediaIngested(event);
  });
  return unsubscribe;
}, []);
```

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
# Using curl
TOKEN=$(curl -s -X POST "http://localhost:8000/v1/auth/bypass" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{"email": "test@example.com"}' | jq -r '.access_token')

# Using HTTPie (alternative)
TOKEN=$(http POST localhost:8000/v1/auth/bypass \
  Content-Type:application/json \
  X-API-Key:dev-api-key-12345 \
  email=test@example.com --print=b | jq -r '.access_token')
```

2. **Use token in API calls**:
```bash
# Test media objects (curl)
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Key: dev-api-key-12345" \
     "http://localhost:8000/v1/media?limit=5"

# Test media objects (HTTPie)
http GET localhost:8000/v1/media limit==5 \
  Authorization:"Bearer $TOKEN" \
  X-API-Key:dev-api-key-12345

# Test storage browse (curl)
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Key: dev-api-key-12345" \
     "http://localhost:8000/v1/storage/browse"

# Test storage browse (HTTPie)
http GET localhost:8000/v1/storage/browse \
  Authorization:"Bearer $TOKEN" \
  X-API-Key:dev-api-key-12345
```

**Note**: 
- Auth bypass only works when `AUTH_BYPASS_ENABLED=true` and the email is in `AUTH_BYPASS_EMAILS` environment variables
- Both `curl` and `http`/`https` (HTTPie) commands are available for API testing
- HTTPie often provides cleaner syntax for JSON APIs

## Database Management

### Migrations
- **Alembic Integration**: Database schema managed via Alembic migrations
- **Automatic Seeding**: Default roles seeded via migration (not app startup)
- **Migration Service**: Dedicated Docker service ensures migrations run before app starts
- **Performance Indexes**: Comprehensive indexing for auth and media tables

### Recent Migrations
- `e52b568743dc_seed_default_roles.py`: Seeds administrator, member, active, sustainer roles
- `9bd71a7c2a0d_add_missing_performance_indexes.py`: Adds 31 performance indexes
  - Users table: lastname/firstname, is_active, created_at, stytch_user_id
  - User roles: user_id, role_id indexes for join performance
  - Media objects: file attributes, timestamps, status combinations
  - Composite indexes for complex query patterns

### Performance Optimizations
- **Virtual Scrolling**: TableVirtuoso handles 1,700+ user records efficiently
- **Database Indexing**: Comprehensive indexes for all common query patterns
- **Lazy Loading**: Components load data on demand
- **Rate Limiting**: Prevents abuse of expensive operations
- **Connection Pooling**: SQLAlchemy connection pooling for database efficiency

## Docker Compose Setup

The application runs in Docker containers orchestrated with Docker Compose.

### Backend Services

- `postgres`: PostgreSQL 17 database with pgvector extension (port 5432)
  - Includes healthcheck with pg_isready for reliable startup
- `redis`: Redis 7 for task queue (port 6379)
- `migrate`: Dedicated migration service ensures database is ready before app starts
- `backend`: FastAPI application (port 8000)
- `ingest-orchestrator`: Single RQ worker for task orchestration
- `ingest-worker`: RQ workers for parallel processing (8 replicas)

### Frontend Services

- `frontend`: Next.js development server (port 3000)
- Uses named volumes for node_modules and .next cache
- Volume mounts for hot reloading

### Service Dependencies

- Postgres includes healthcheck for reliable startup sequence
- Migrate service depends on postgres being healthy
- Backend depends on migrate service completion, postgres, and redis
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

### Backend Architecture Guidelines

- **Streaming Responses**: Use FastAPI's native async streaming instead of creating new event loops
- **Singleton Pattern**: Implement for expensive-to-create clients (storage, Redis, S3)
- **Resource Management**: Always implement proper cleanup in `finally` blocks for streaming endpoints
- **Long-running Processes**: Monitor resource accumulation over time, especially in containerized environments
- **Event Loop Management**: Never create new event loops in FastAPI endpoints - reuse the existing one

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

**LibrarySidebar** (`src/components/LibrarySidebar.tsx`):
- App-wide navigation sidebar using shadcn/ui Sidebar components
- Sections: Library (Photos, Search), By League Year, Admin, Me
- Active state detection based on current pathname
- Conditional admin menu items based on user roles

**MediaModal** (`src/components/MediaModal.tsx`):
- Reusable modal for photo viewing
- Supports ESC key, backdrop click, and button close
- Generic container accepting any content as children

**Integration Points**:
- Library pages (`/library`, `/library/[...path]`) use LibraryView directly
- Component test pages available at `/components/*` for development
- All components follow TypeScript strict mode with proper interfaces

## Production Debugging & Performance

### Resource Leak Prevention

Tagline implements several patterns to prevent resource accumulation in long-running containers:

**Singleton Patterns**:
- `StorageProviderSingleton`: Prevents creating new Dropbox/filesystem clients per request
- `S3BinaryStorage`: Reuses S3 client connections with proper pooling
- `RedisEventPublisher`: Single Redis connection for pub/sub events
- `Database Engine`: Connection pooling with NullPool for containerized environments

**Known Issues & Solutions**:
- **SSE Event Loops**: Fixed resource leak where SSE connections created new event loops
- **Connection Accumulation**: Monitor Redis connections and implement connection TTL
- **Memory Growth**: Use diagnostics endpoints to track resource usage over time

### Performance Debugging Methodology

For production slowness issues:

1. **Isolate the problem scope**:
   ```bash
   # Test direct FastAPI endpoints vs routed endpoints
   curl -w "Time: %{time_total}s\n" https://app.com/openapi.json
   curl -w "Time: %{time_total}s\n" https://app.com/v1/health
   ```

2. **Check resource accumulation**:
   ```bash
   # Redis connections
   redis-cli CLIENT LIST | wc -l
   
   # Use diagnostics endpoints
   http GET localhost:8000/v1/diagnostics/detailed \
     Authorization:"Bearer $TOKEN" X-API-Key:dev-api-key-12345
   ```

3. **Look for patterns**:
   - Time-based degradation (hours/days)
   - Route-specific vs global slowness
   - Resource type (memory, connections, file descriptors)

### UI Performance Considerations

**PhotoThumbnail State Management**:
- Tracks processing history to prevent UI flashing during ingestion
- Continues showing spinner until image actually loads (prevents icon → spinner → icon → thumbnail flash)
- Limits spinners to actively processing items plus recently completed items

## Stakeholder Context

- Primary users are Junior League of Los Angeles members
- Photo organization and discovery are key use cases
- Demo-by-screenshot capability was important for initial stakeholder presentation
- Future demos and stakeholder feedback sessions are planned
- Focus on practical usability over complex features for MVP