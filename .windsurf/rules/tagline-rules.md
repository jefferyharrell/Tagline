---
trigger: always_on
---

# Tagline Project Rules

## Project Context
- Tagline is a media management application for the Junior League of Los Angeles (JLLA).
- Primary purpose: Help organize photos currently stored on Dropbox, making them searchable and identifiable.
- Two-silo architecture: content silo and metadata silo, both designed to be pluggable.
- Target users: JLLA members with varying technical expertise.

## Authentication System
- Uses Stytch for magic link authentication.
- Implements a pre-approved email whitelist (~1500 JLLA members).
- Multi-role user system: 'member', 'admin', 'active', 'sustainer'.
- Users may have multiple roles simultaneously.
- JWT tokens for session management.

## Tech Stack
- Backend: Python with FastAPI
- Database: PostgreSQL (via Neon)
- Frontend: Next.js 15, React 19, TypeScript
- Styling: Tailwind CSS
- Authentication: Stytch React SDK with official provider pattern
- Storage: Cloud storage for original media, thumbnails, and proxies

## Code Style & Architecture
- Frontend:
  - Use TypeScript strictly with proper type definitions, avoid 'any' type.
  - Follow React best practices with functional components and hooks.
  - Use official Stytch provider pattern (not custom AuthProvider).
  - Keep components small and focused on a single responsibility.
  - Implement responsive design for all UI components.

- Backend:
  - Use a layered architecture: domain models, ORM models, API schemas.
  - MediaObject is the core data model with metadata, thumbnails, and proxies.
  - Implement proper error handling and validation.
  - Follow RESTful API design principles.

## Known Issues & Constraints
- SIMPLIFY, DON'T OVERCOMPLICATE:
  - Prefer straightforward solutions over complex architectures.
  - When multiple approaches exist, recommend the simpler one.
  - Avoid introducing unnecessary abstractions or dependencies.
  - Focus on getting features working before optimizing.

- NO HALLUCINATED FEATURES:
  - Only implement what is explicitly requested.
  - Don't assume the existence of endpoints, components, or models.
  - Verify file paths and imports before suggesting code changes.
  - If uncertain about implementation details, ASK for clarification.

## Implementation Guidelines
- Authentication Flow:
  - First check email eligibility before showing Stytch login UI.
  - Use the StytchProvider at the root layout level.
  - Leverage Stytch hooks instead of manual client instantiation.
  - Implement smooth user feedback during authentication processes.

- Media Handling:
  - Support efficient loading and display of images.
  - Implement proper caching and optimization strategies.
  - Consider bandwidth limitations when designing media display features.

## Project Workflow
- Split workflow: planning in Claude Desktop, implementation in Windsurf.
- Keep commits focused and descriptive.
- Prioritize working features over perfect architecture.
