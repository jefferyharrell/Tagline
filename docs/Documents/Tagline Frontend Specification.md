---
tags:
  - tagline
  - frontend
  - specification
date: 2025-05-17
author: Alpha
---
## Overview

This document provides a comprehensive specification for the Tagline frontend application. Tagline is a media management system designed for the Junior League of Los Angeles (JLLA) to organize and search their photo collection. The frontend is built using Next.js, TypeScript, Tailwind CSS, and shadcn/ui components.

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 15.x | React framework with server components |
| TypeScript | 5.x | Type-safe JavaScript |
| Tailwind CSS | 4.x | Utility-first CSS framework |
| shadcn/ui | latest | Component library based on Radix UI |
| Stytch | latest | Authentication provider for magic link login |

## Application Structure

The frontend application follows the Next.js App Router architecture with TypeScript for type safety.

```
src/
├── app/                    # App Router pages and layouts
│   ├── (auth)/             # Authentication routes
│   │   ├── login/          # Login page
│   │   ├── auth/callback/  # Auth callback handler
│   ├── (protected)/        # Protected routes (require auth)
│   │   ├── dashboard/      # Main dashboard
│   │   ├── media/          # Media browsing and management
│   │   ├── upload/         # Upload interface
│   │   ├── search/         # Search interface
│   │   ├── admin/          # Admin panel (role-restricted)
│   ├── api/                # API routes
│   │   ├── auth/           # Auth-related API endpoints
│   │   ├── media/          # Media-related API endpoints
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Landing page
├── components/             # Reusable components
│   ├── ui/                 # shadcn/ui components
│   ├── auth/               # Authentication components
│   ├── media/              # Media-related components
│   ├── layout/             # Layout components
│   ├── forms/              # Form components
├── lib/                    # Utility functions and shared code
│   ├── auth/               # Auth-related utilities
│   ├── api/                # API client and utilities
│   ├── types/              # TypeScript type definitions
│   ├── utils/              # General utilities
├── hooks/                  # Custom React hooks
├── styles/                 # Global styles and Tailwind config
├── providers/              # React context providers
```

## Authentication

Authentication will be implemented using Stytch for magic link authentication with a multi-role user system.

### User Roles

- **member**: Basic access to view and search media
- **admin**: Administrative privileges for user management
- **active**: Active JLLA members
- **sustainer**: Sustainer JLLA members

### Authentication Flow

1. **Email Eligibility Check**:
   - User enters email on login page
   - Frontend verifies email against backend whitelist
   - Only pre-approved emails can proceed to login

2. **Magic Link Authentication**:
   - Eligible users receive a magic link via Stytch
   - Link redirects to callback URL
   - Session token is exchanged with backend for JWT
   - JWT contains user ID, email, and roles

3. **Session Management**:
   - JWT stored in localStorage or secure HTTP-only cookie
   - Auth provider context manages user state
   - Protected routes check for valid session
   - Role-based access control for restricted areas

### Authentication Components

1. **AuthProvider**:
   - Context provider for authentication state
   - Manages user sessions and role information
   - Provides login/logout functions
   - Handles token refresh

2. **LoginPage**:
   - Two-step login process (eligibility check → magic link)
   - Clean, branded interface
   - Error handling for invalid emails

3. **ProtectedRoute**:
   - Higher-order component for route protection
   - Configurable required roles
   - Redirect to login for unauthenticated users
   - Redirect to unauthorized page for insufficient permissions

## User Interface Design

### Design System

- **Color Palette**:
  - Accent: `#d32a40` (JL Red)
  - Background: `#FFFFFF` (white)
  - Text: `#000000` (black)

- **Typography**:
  - Primary font: Arial (sans-serif)
  - Heading font: Arial (sans-serif)
  - Base font size: 16px
  - Scale: 1.25 ratio

- **Spacing System**:
  - Based on 4px increments
  - Consistent spacing using Tailwind's default scale

- **Component Styling**:
  - Use shadcn/ui components with custom theme
  - Consistent rounded corners (0.5rem)
  - Subtle shadows for elevation
  - Interactive states for all clickable elements

### Responsive Design

- Mobile-first approach
- Breakpoints:
  - sm: 640px
  - md: 768px
  - lg: 1024px
  - xl: 1280px
  - 2xl: 1536px

- Layout adapts to screen size:
  - Mobile: Single column, stacked navigation
  - Tablet: Two columns, sidebar navigation
  - Desktop: Multi-column, expanded navigation

### Accessibility

- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader compatibility
- Sufficient color contrast
- Focus indicators for interactive elements
- Aria labels and roles where appropriate

## Core Features

### Navigation

The application will use a responsive navigation system:
- Mobile: Bottom navigation bar with icons
- Desktop: Sidebar navigation with icons and labels
- Admin features only visible to admin users

### Dashboard

The dashboard provides an overview of the media collection:
- Recent uploads
- Statistics (total media, tags, categories)
- Quick search
- Activity feed
- Favorites or recently viewed

### Media Browser

The central feature of the application and the default route ("/"), allowing users to:
- View media in grid or list layout
- Filter by date, tags, metadata
- Sort by various attributes
- View detailed information for individual items
- Perform batch operations (tag, download)

#### Media Grid View
- Responsive grid layout (1-5 columns based on screen size)
- Media thumbnails with hover state
- Quick action buttons (favorite, view details)
- Infinite scroll or pagination

#### Media List View
- Tabular view with columns for key metadata
- Sortable columns
- Compact representation for scanning many items

#### Media Detail View
- Large media preview
- Complete metadata display
- Editing capabilities (for authorized users)
- Related media suggestions
- Download options
- Sharing functionality

### Search Interface

Comprehensive search capabilities:
- Full-text search across metadata
- Advanced filters (date ranges, tags, keywords)
- Saved searches
- Search history
- Instant results as you type
- Exportable search results

### Admin Panel

Administrative functions (admin role only):
- User management
  - View all users
  - Add/remove users from whitelist
  - Assign/revoke roles
- System status
  - Storage usage
  - Recent activity
  - Error logs
- Batch operations
  - Trigger media scans
  - Batch metadata updates

## API Integration

The frontend will communicate with the Tagline backend API:

### Authentication Endpoints
- `POST /api/auth/check-eligibility`: Verify email is in whitelist
- `POST /api/auth/session`: Exchange Stytch token for JWT
- `GET /api/auth/me`: Get current user profile

### Media Endpoints
- `GET /api/media`: List media objects with pagination and filtering
- `GET /api/media/:id`: Get single media object details
- `POST /api/media`: Upload new media
- `PATCH /api/media/:id`: Update media metadata
- `DELETE /api/media/:id`: Delete media
- `GET /api/media/:id/thumbnail`: Get media thumbnail
- `GET /api/media/:id/download`: Download original media

### Admin Endpoints
- `GET /api/admin/users`: List all users
- `POST /api/admin/users`: Add new user to whitelist
- `DELETE /api/admin/users/:id`: Remove user
- `PATCH /api/admin/users/:id/roles`: Update user roles
- `POST /api/admin/scan`: Trigger media scan

### API Client
The frontend will use a custom API client:
- Type-safe API requests with TypeScript
- Automatic JWT inclusion in requests
- Error handling and retry logic
- Request/response interceptors
- Caching where appropriate

## State Management

- **React Context**: Authentication state and application preferences
- **SWR or TanStack Query**: Data fetching and caching
- **Form State**: React Hook Form for complex forms
- **URL State**: Router query parameters for sharable states

## Performance Optimization

- Server components for static parts of the UI
- Client components for interactive elements
- Image optimization with Next.js Image component
- Code splitting and lazy loading
- Memoization of expensive components
- Virtualized lists for large data sets
- Prefetching and preloading of likely navigation targets

## Error Handling

- Comprehensive error boundary implementation
- Graceful degradation of features
- User-friendly error messages
- Detailed error logging (client-side)
- Fallback UI for failed components
- Retry mechanisms for transient errors

## Testing Strategy

- **Unit Tests**: Components and utilities using Jest and React Testing Library
- **Integration Tests**: User flows and multi-component interactions
- **E2E Tests**: Complete application flows using Playwright
- **Visual Regression Tests**: UI component consistency 
- **A11y Tests**: Accessibility validation

## Build and Deployment

- TypeScript strict mode enabled
- ESLint and Prettier for code quality
- Husky for pre-commit hooks
- CI/CD pipeline integration
- Docker-based deployment
- Environment-specific configuration

## Environment Variables

```
# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key

# Stytch
NEXT_PUBLIC_STYTCH_PUBLIC_TOKEN=public-token-live-xxxx
STYTCH_SECRET_TOKEN=secret-live-xxxx
STYTCH_PROJECT_ID=project-live-xxxx

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
API_KEY=your-api-key
```

## Implementation Plan

### Phase 1: Foundation
- Project setup with Next.js, TypeScript, Tailwind, shadcn/ui
- Authentication system implementation
- Basic navigation and layouts
- API client configuration

### Phase 2: Core Features
- Media browser (grid and list views)
- Media detail view
- Basic search functionality
- Upload interface

### Phase 3: Advanced Features
- Advanced search capabilities
- Admin panel
- Batch operations
- Offline support

### Phase 4: Polish
- Performance optimization
- Comprehensive testing
- Documentation
- Final UI polish and animations

## Conclusion

This specification provides a comprehensive guide for implementing the Tagline frontend application. The combination of Next.js, TypeScript, Tailwind CSS, and shadcn/ui provides a modern, maintainable foundation for building a robust media management interface that meets the needs of the Junior League of Los Angeles.

The implementation will focus on usability, performance, and maintainability while ensuring the application can grow and adapt to future requirements.
