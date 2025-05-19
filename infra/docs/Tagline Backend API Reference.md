---
tags:
  - tagline
date: 2025-04-30
version: 1.0.0
---

This document provides a complete, detailed schema for the Tagline REST API. All endpoints require authentication via the `X-API-Key` header, which is set via the `API_KEY` environment variable.

---

## Data Models

### MediaObject
Represents a media item managed by the application.

```json
{
  "id": "<UUID>",
  "object_key": "<string>",
  "created_at": "<UTC timestamp>",
  "updated_at": "<UTC timestamp>",
  "object_metadata": { /* see METADATA.md */ }
}
```

- `id` (string, UUID): Unique identifier for the media object
- `object_key` (string): Storage path or unique key in the storage provider
- `last_modified` (string, ISO 8601 UTC): Last modification timestamp
- `metadata` (object): See [[Media Object Metadata Structure]] for structure and conventions

### PaginatedMediaObjectList (Response)
Returned by list endpoints.

```json
{
  "items": [MediaObject, ...],
  "total": 123,
  "limit": 100,
  "offset": 0,
  "pages": 2
}
```

- `items` (array): List of MediaObject
- `total` (integer): Total number of items available
- `limit` (integer): Page size
- `offset` (integer): Offset for pagination
- `pages` (integer): Total number of pages

### ErrorResponse (Response)
Standard error response for all endpoints.

```json
{
  "detail": "Human-readable error message"
}
```

## Endpoint Categories

### Media Object Endpoints

#### List Media Objects
| Method | Path | Description | Parameters | Response |
|--------|------|-------------|------------|----------|
| GET | `/v1/media` | List media objects | - `limit` (int, optional): Number of items per page<br>- `offset` (int, optional): Pagination offset<br>- `shuffle` (bool, optional): Randomize order | Paginated list of media objects |

#### Update Media Object
| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| PATCH | `/v1/media/{id}` | Partially update media object | Partial MediaObject fields | Updated MediaObject |

#### Retrieve Media Object
| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/v1/media/{id}` | Get full details of a media object | Full MediaObject |

#### Retrieve Media Object Data
| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/v1/media/{id}/data` | Get raw file contents | Raw file data |

#### Retrieve Media Object Thumbnail
| Method | Path | Description | Parameters | Response |
|--------|------|-------------|------------|----------|
| GET | `/v1/media/{id}/thumbnail` | Get media object thumbnail | - `size` (int[], optional): Desired thumbnail dimensions | 512x512 JPEG thumbnail |

**Note:** Thumbnails are generated using Pillow with HEIC support for JPEG and HEIC images.

### Ingest Endpoints

#### Initiate Media Scan
| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/v1/ingest` | Start background media object scanning | Ingest task details |

#### Get Ingest Task Status
| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/v1/ingest/status` | Check status of ongoing ingest task | Task progress information |

### Database Endpoints

#### Scan Database
| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/v1/database/scan` | Trigger database scan for new media | Scan task details |

#### Database Health
| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/v1/database/health` | Check database connection and status | Database health metrics |

## Authentication

### API Key Requirements
- All requests MUST include `X-API-Key` header
- API key MUST be a cryptographically secure random string
- API key is set via the `API_KEY` environment variable
- Key rotation is supported without system downtime (TBD)

### Common Error Codes
- `invalid_api_key`: Authentication failed
- `resource_not_found`: Requested resource does not exist
- `validation_error`: Request payload invalid

## Status Codes

| Endpoint                        | Method | Status Code | Description                        |
|---------------------------------|--------|-------------|------------------------------------|
| /v1/media                       | GET    | 200         | Success (paginated list)           |
|                                 |        | 401         | Unauthorized                       |
| /v1/media/{id}                  | GET    | 200         | Success (single object)            |
|                                 |        | 404         | Not found                          |
|                                 |        | 401         | Unauthorized                       |
| /v1/media/{id}/thumbnail        | GET    | 200         | Success (image data)               |
|                                 |        | 404         | Not found                          |
|                                 |        | 401         | Unauthorized                       |
| /v1/media/{id}/data             | GET    | 200         | Success (file data)                |
|                                 |        | 404         | Not found                          |
|                                 |        | 401         | Unauthorized                       |
| /v1/media/{id}                  | PATCH  | 200         | Success (object updated)           |
|                                 |        | 404         | Not found                          |
|                                 |        | 401         | Unauthorized                       |
| /v1/db/scan                     | POST   | 200         | Scan started                       |
|                                 |        | 401         | Unauthorized                       |
| /v1/health                      | GET    | 200         | Health check OK                    |

---

## Validation Rules

### MediaObject
- `id`: string, UUID, required, immutable
- `object_key`: string, required, unique within provider, UTF-8, max length varies from 260 bytes up to 4000 bytes depending on the provider
- `created_at`: string, ISO 8601 UTC, required
- `updated_at`: string, ISO 8601 UTC, required
- `object_metadata`: object, optional, must be JSON-serializable

### UpdateMediaObjectRequest
- `object_metadata`: object, optional, must be JSON-serializable
  - `description`: string, optional, max length 1024
  - `keywords`: array of strings, optional, each tag max length 64

### Pagination Parameters
- `limit`: integer, optional, min 1, max 500, default 100
- `offset`: integer, optional, min 0, default 0
- `shuffle`: boolean, optional

---

## Error Response Schema
All error responses have the following structure:
```json
{
  "detail": "Human-readable error message"
}
```
