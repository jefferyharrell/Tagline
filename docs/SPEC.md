# Project Specification

**Version:** 1.0.0
**Last Updated:** 2025-04-30

> **Note:**
> This document is a living specification. It will be revised and extended as the project evolves. All agents and contributors MUST refer to the latest version before implementing or reviewing any requirements.

> **RFC 2119 Compliance:**
> This spec uses **MUST**, **SHOULD**, and **MAY** as defined by [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

## Name

The name "Tagline" is provisional and subject to change. Try to avoid using it in code as much as possible.

## Purpose

Tagline is a web application for managing media objects (e.g., photos) and their metadata.

## Glossary

### Technical Terms
- **API Key**: A shared secret used for request authentication, preventing unauthorized access to the application.
- **Pagination**: A technique for dividing large sets of data into smaller, manageable pages with `limit` and `offset` parameters.
- **Media Object**: A digital file (image, video, audio) with associated metadata, managed by the application.
- **Storage Provider**: An abstraction layer for file storage, supporting multiple backend implementations (local filesystem, cloud storage).
- **Thumbnail**: A smaller, preview-sized version of a media object used for quick visual representation.

### Domain-Specific Terms
- **Object Key**: A unique identifier for a media object within a storage system, similar to a file path.
- **Metadata**: Descriptive information about a media object, such as creation date, description, keywords, or other attributes.
- **Raw Data**: The original, unprocessed file content of a media object.

### Performance Terms
- **Concurrent Users**: The number of simultaneous users interacting with the application.
- **Response Time**: The duration between a user request and the server's complete response.

### Development Terms
- **Environment Variable**: A configurable value that can change the behavior of software without modifying code.
- **Plugin**: An optional, modular component that extends the core functionality of an application.

### Testing Terms
- **Faker**: A library used to generate realistic, randomized test data.
- **Mocking**: Creating simulated objects that mimic the behavior of real objects for testing.
- **Coverage**: A measure of how much of the source code is executed during testing.

## Architecture

```
+---------------------------------------+
|           Frontend                    |
+---------------------------------------+
              |
              | X-API-Key: <shared-secret>
              v
+---------------------------------------+
|             FastAPI Backend           |
+---------------------------------------+
          |                    |
+------------------+ +------------------+
|                  | |                  |
| Storage Provider | | ORM/Database     |
| Abstraction      | | (Postgres)       |
|                  | |                  |
+------------------+ +------------------+
|                  | |                  |
| filesystem,      | | Database Tables  |
| dropbox, etc.    | | (photos, etc.)   |
|                  | |                  |
+------------------+ +------------------+
```

## Ingest Task

The application MUST support a non-blocking, long-running background ingest task that scans the configured storage provider for new media objects and adds them to the database. This task should be initiated via an API endpoint and can be run periodically or on-demand. Information about the progress of the task should be available to the application on demand.

### Thumbnails

- Thumbnails will be generated during the scan step (also called "ingest").
- Thumbnails are stored in the database as byte arrays.
- Thumbnails are 512 by 512 pixels, cropped (not padded).
- Thumbnails are stored in JPEG format.

## Data Model

The main data model is called `MediaObject`.

```json
{
    "id": "<UUID>",
    "object_key": "<string>",
    "last_modified": "<UTC timestamp>",
    "metadata": {}
}
```

- See [METADATA.md](./METADATA.md) for the structure, standard fields, and conventions for the `metadata` property.

### Fields

| Field         | Type           | Description                                                     | Constraints                     |
|--------------|----------------|----------------------------------------------------------------|---------------------------------|
| `id`         | UUID           | Unique identifier for the media object                          | Primary key, immutable          |
| `object_key` | String         | Storage path or unique identifier in the storage provider       | Indexed, unique within provider |
| `last_modified` | DateTime     | Timestamp of the last modification, stored in UTC               | Automatically updated           |
| `metadata`   | JSON Object    | Flexible metadata associated with the media object              | See METADATA.md                 |

### ORM and Migrations

- The project uses SQLAlchemy as the ORM (Object-Relational Mapper) for database access and modeling.
- Alembic is used for managing database schema migrations.

## API

The API is a RESTful API built on FastAPI. It is versioned using the URL prefix `/v1`.

**All details of API endpoints, request/response schemas, authentication, and validation rules are specified in [`docs/API.md`](./API.md).**

- Do not duplicate endpoint or schema details here.
- Refer to API.md for the complete, up-to-date API contract.

## Storage Provider Abstraction

The application uses a storage provider abstraction layer to manage media files. The storage provider MUST support the following operations:

- List (in default order, optionally paginated)
- Find (by metadata attributes)
- Retrieve (by ID)
- Create (new media object)
- Update (existing media object)
- Delete (media object)

The storage provider MUST be configured via environment variables, never hardcoded in the source code. The application MUST support multiple storage providers, with the default being a local filesystem. Additional storage providers (e.g., Dropbox, S3) MAY be added as plugins, each with its own configuration and implementation. The application MUST be able to switch between storage providers dynamically, with the choice being configurable via environment variables.

## Storage Provider Interface

### `StorageProviderBase` Abstract Base Class

The `StorageProviderBase` defines a standardized interface for media storage operations. All storage providers MUST implement the following methods:

#### Method Signatures

```python
class StorageProviderBase(ABC):
    @abstractmethod
    async def save(
        self,
        object_key: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a media object to storage.

        Args:
            object_key: Unique identifier for the object
            data: Raw file contents
            metadata: Optional metadata associated with the object

        Returns:
            Confirmed storage location or object identifier
        """
        pass

    @abstractmethod
    async def retrieve(
        self,
        object_key: str
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Retrieve a media object from storage.

        Args:
            object_key: Unique identifier for the object

        Returns:
            Tuple of (raw_data, metadata)
        """
        pass

    @abstractmethod
    async def delete(
        self,
        object_key: str
    ) -> bool:
        """
        Delete a media object from storage.

        Args:
            object_key: Unique identifier for the object

        Returns:
            True if deletion was successful, False otherwise
        """
        pass

    @abstractmethod
    async def list(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List media objects in storage.

        Args:
            prefix: Optional path/namespace prefix
            limit: Maximum number of objects to return
            offset: Number of objects to skip

        Returns:
            List of object metadata
        """
        pass

    @abstractmethod
    async def generate_thumbnail(
        self,
        object_key: str,
        size: Tuple[int, int] = (100, 100)
    ) -> bytes:
        """
        Generate a thumbnail for a media object.

        Args:
            object_key: Unique identifier for the object
            size: Desired thumbnail dimensions (width, height)

        Returns:
            Thumbnail image bytes
        """
        pass
```

### Provider-Specific Considerations

- Each storage provider implementation MUST handle its own authentication and connection management
- Providers SHOULD implement robust error handling
- Async methods are required to support concurrent operations
- Providers MUST be configurable via environment variables

### Example Provider Implementation

```python
class LocalFilesystemProvider(StorageProviderBase):
    def __init__(self, base_path: Path):
        self.base_path = base_path

    async def save(self, object_key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None):
        # Local filesystem specific implementation
        pass

    # ... other method implementations
```

### Performance Expectations

- Save/Retrieve operations SHOULD complete within 500ms for objects under 10MB
- Thumbnail generation SHOULD complete within 250ms
- List operations MUST support pagination and return metadata efficiently

## Logging

The application MUST implement logging using Python's standard `logging` module:

- All logs MUST be written to stdout
- Log format MUST be human-readable plain text
- Log level MUST be configurable via environment variable `LOG_LEVEL`
- Default log level is `INFO`

Logging Configuration:
- Supported log levels: DEBUG, INFO, WARN, ERROR, CRITICAL
- Log messages MUST include:
  - Log level
  - Descriptive message

## Performance Considerations

Given the application's intended scale (dozens of users), performance optimization will prioritize simplicity and maintainability over extreme efficiency:

- The application SHOULD comfortably handle up to 100 concurrent users
- Media object retrieval MUST complete within 500ms for objects under 10MB
- Thumbnail generation SHOULD complete within 250ms
- Batch operations (like media scanning) MAY take longer but SHOULD provide progress updates

Scaling Expectations:
- No specialized high-performance infrastructure required
- Standard cloud/container resources (2-4 CPU cores, 4-8GB RAM) are sufficient
- Vertical scaling is preferred over horizontal scaling for this application's scope

Optimization Principles:
- Prefer readable, maintainable code over premature optimization
- Use database indexing for common query patterns
- Implement basic caching for frequently accessed media objects
- Monitor and log performance during actual usage to guide future improvements

## Development Environment

The project uses `just` for task automation and environment management. Developers MUST use the following workflow:

### Prerequisites
- Python 3.12+
- `just` command runner
- `pip` for dependency management
- `venv` for virtual environment management

### Development Commands
- `just setup`: Initialize development environment
- `just format`: Format code
- `just lint`: Run linters and type checkers
- `just test`: Run all tests
- `just up`: Spin up Docker Compose stack
- `just down`: Tear down Docker Compose stack
- `just everything`: Run all checks (format, lint, test)

Environment Configuration:
- Use `.env` for local environment variables
- MUST NOT commit sensitive information to version control
- Provide a `.env.example` with placeholder values

### Testing Strategy

#### Test Framework
- Test runner: `pytest`
- Supported test types: Unit Tests, End-to-End (E2E) Tests

#### Unit Tests
- Located in `tests/unit/`
- Test individual components, functions, and classes in isolation
- MUST run without external dependencies
- Use mocking and patching for complex dependencies
- Aim for 90%+ code coverage

#### End-to-End (E2E) Tests
- Located in `tests/e2e/`
- Use `HTTPX` to interact with dev server running in Docker
- Test complete request/response cycles
- Validate API contract and integration
- Simulate real-world usage scenarios

#### Testing Principles
- All tests MUST be deterministic
- Tests SHOULD be independent and repeatable
- Avoid side effects in test environments
- Use fixtures for common test setup
- Clearly separate test data from test logic

#### Test Coverage Requirements
- Minimum coverage: 90% for all code paths
- Focus on critical paths and edge cases
- Use `pytest-cov` for coverage reporting

#### Test Data Generation

The project uses the `Faker` library to generate realistic, randomized test data for comprehensive testing. This approach ensures:
- Consistent, reproducible test scenarios
- Realistic mock data across different test runs
- Coverage of diverse input types and edge cases

Test data generation principles:
- Use `Faker` to create synthetic media objects with realistic metadata
- Randomize object keys, descriptions, and timestamps
- Generate test data that mimics real-world complexity
- Ensure predictable random generation for reproducible tests

Example test data generation:
```python
from faker import Faker
from uuid import uuid4

fake = Faker()
test_media_object = {
    'id': str(uuid4()),
    'object_key': fake.file_path(depth=3),
    'metadata': {
        'description': fake.sentence(),
    }
}
```
