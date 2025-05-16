---
tags:
  - tagline
date: 2025-04-30
---

This document describes the structure, conventions, and recommended fields for the `object_metadata` property of a MediaObject in the Tagline application.

---

## Overview

- The `object_metadata` field is a flexible, JSON-serializable object attached to each MediaObject.
- It is intended to store descriptive, searchable, or user-defined information about the media item.
- The structure is designed for extensibility and forward compatibility.

## General Structure

```json
{
  "description": "A short description of the media object.",
  "keywords": ["keyword1", "keyword2"],
  // ...additional fields TBA...
}
```

- All fields are optional unless otherwise specified.
- Unknown fields SHOULD be ignored by clients to allow for future expansion.

## Standard Fields

| Field        | Type              | Description                                 | Constraints                |
|--------------|-------------------|---------------------------------------------|----------------------------|
| description  | string            | Short, human-readable description           | Max length: 1024           |
| keywords         | array of strings  | List of  keywords                    | Each tag max length: 64    |

## Extensibility

- Custom fields SHOULD use lower_snake_case naming.
- Follow the example set by Dublin Core when modeling metadata.
- Avoid using names that conflict with standard fields.

## Examples

### Minimal Metadata
```json
{}
```

### With Description and Keywords
```json
{
  "description": "Vacation photo from 2024.",
  "keywords": ["vacation", "beach", "family"]
}
```

## Guidelines

- All metadata values MUST be JSON-serializable.
- Use UTF-8 encoding for all string values.
- Clients SHOULD ignore unknown fields for forward compatibility.

## Pydantic Metadata Model Example

Below is an example of a Pydantic model for the `object_metadata` property, reflecting the structure and constraints described above:

```python
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator

class ObjectMetadataModel(BaseModel):
    description: Optional[str] = Field(
        default=None, max_length=1024, description="Short, human-readable description."
    )
    keywords: Optional[List[str]] = Field(
        default=None, description="List of keywords. Each keyword max length: 64."
    )

    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v):
        if v is not None:
            for tag in v:
                if len(tag) > 64:
                    raise ValueError("Each keyword must be at most 64 characters long.")
        return v

    model_config = {
        'extra': 'allow'  # Allow custom fields for extensibility
    }

```

- This model enforces the constraints for `description` and `keywords`.
- Additional custom fields are allowed for extensibility.
- Use this model as the type for the `object_metadata` field in your MediaObject Pydantic model.

---

For questions or proposals for new standard fields, please open an issue or submit a pull request.
