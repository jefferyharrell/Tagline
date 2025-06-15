# Structured Logging Standards

This document defines the standards and patterns for structured logging in the Tagline backend.

## Core Principles

1. **All logs must use structured key-value pairs** - No f-string interpolation
2. **Consistent field naming** across all modules
3. **Hierarchical operation naming** for easy filtering
4. **Performance-aware logging** with minimal overhead
5. **Debug-friendly context** in all error conditions

## Standard Field Names

### Required Fields
- `operation`: String identifying the operation type (see naming convention below)
- `duration_ms`: Float for operation timing (when applicable)

### Common Context Fields
- `object_key`: Media object identifier
- `path`: File system or storage path
- `user_id`: User identifier for request context
- `file_size`: File size in bytes
- `file_mimetype`: MIME type of files
- `status`: Operation status (success, failed, pending, etc.)
- `provider`: Storage provider name (dropbox, filesystem)
- `table`: Database table name
- `endpoint`: API endpoint path
- `method`: HTTP method
- `job_id`: Background job identifier

### Error Fields
- `error_type`: Exception class name
- `error_message`: Exception message
- `traceback`: Full traceback (debug mode only)

## Operation Naming Convention

Use hierarchical naming: `{module}_{action}`

### Database Operations
- `db_query` - SELECT operations
- `db_create` - INSERT operations  
- `db_update` - UPDATE operations
- `db_delete` - DELETE operations
- `db_bulk_insert` - Bulk INSERT operations
- `db_migration` - Schema migrations

### Storage Operations
- `storage_list` - List files/folders
- `storage_read` - Read file content
- `storage_write` - Write file content
- `storage_delete` - Delete files
- `storage_metadata` - Get file metadata
- `storage_download` - Download operations

### API Operations
- `api_request_start` - Request initiation
- `api_request_complete` - Request completion
- `api_error` - Request error handling
- `api_auth` - Authentication operations

### Media Processing
- `media_ingest` - Media ingestion pipeline
- `media_thumbnail` - Thumbnail generation
- `media_proxy` - Proxy image creation
- `media_metadata` - Metadata extraction

### Background Tasks
- `job_start` - Job initiation
- `job_complete` - Job completion
- `job_error` - Job failure
- `job_retry` - Job retry attempts

## Logging Templates

### Database Operations
```python
# Query operation
logger.debug(
    "Querying database table",
    operation="db_query",
    table="media_objects",
    object_key=object_key,
    filters={"status": "active"}
)

# Create operation with timing
start_time = time.time()
# ... database operation ...
logger.info(
    "Database record created",
    operation="db_create",
    table="media_objects", 
    object_key=new_object.object_key,
    duration_ms=(time.time() - start_time) * 1000
)

# Error handling
logger.error(
    "Database operation failed",
    operation="db_query",
    table="media_objects",
    object_key=object_key,
    error_type=type(e).__name__,
    error_message=str(e)
)
```

### Storage Operations
```python
# List operation
logger.debug(
    "Listing storage contents",
    operation="storage_list",
    provider="dropbox",
    path=folder_path
)

# Successful operation with metrics
logger.info(
    "Storage operation completed",
    operation="storage_list",
    provider="dropbox", 
    path=folder_path,
    item_count=len(items),
    duration_ms=duration
)

# Download with progress
logger.info(
    "File download completed",
    operation="storage_download",
    provider="dropbox",
    path=file_path,
    file_size=file_size,
    duration_ms=download_time
)
```

### API Operations
```python
# Request logging
logger.info(
    "Processing API request",
    operation="api_request_start",
    endpoint=request.url.path,
    method=request.method,
    user_id=current_user.id if current_user else None
)

# Response logging
logger.info(
    "API request completed",
    operation="api_request_complete", 
    endpoint=request.url.path,
    status_code=200,
    duration_ms=(time.time() - start_time) * 1000,
    response_items=len(response_data) if response_data else 0
)

# Error responses
logger.error(
    "API request failed",
    operation="api_error",
    endpoint=request.url.path,
    status_code=500,
    error_type=type(e).__name__,
    error_message=str(e),
    user_id=current_user.id if current_user else None
)
```

### Background Jobs
```python
# Job initialization (use job logger with bound context)
job_logger = get_job_logger(
    __name__,
    job_id=job_id,
    object_key=object_key,
    operation="media_ingest"
)

job_logger.info("Job started", operation="job_start")

# Progress updates
job_logger.info(
    "Processing step completed",
    operation="media_thumbnail",
    step="generate_thumbnail",
    file_size=file_size,
    duration_ms=step_duration
)

# Job completion
job_logger.info(
    "Job completed successfully", 
    operation="job_complete",
    total_duration_ms=(time.time() - job_start) * 1000,
    files_processed=file_count
)
```

## Performance Guidelines

### Expensive Operations
For operations that might be expensive to compute, use lambda functions or conditional evaluation:

```python
# Good: Only compute if debug logging is enabled
logger.debug(
    "Debug information",
    operation="db_query",
    query_details=lambda: expensive_query_analysis() if logger.isEnabledFor(logging.DEBUG) else None
)

# Better: Use contextual information instead of expensive computation
logger.debug(
    "Complex query executed",
    operation="db_query", 
    table="media_objects",
    join_count=3,
    where_clauses=len(where_conditions)
)
```

### High-Volume Operations
Consider log sampling for very high-volume operations:

```python
# Sample 1% of thumbnail requests
if random.random() < 0.01:
    logger.info(
        "Thumbnail served",
        operation="media_thumbnail",
        object_key=object_key,
        cache_hit=was_cached
    )
```

## Anti-Patterns to Avoid

### ❌ F-string interpolation
```python
logger.info(f"Processing {object_key} with status {status}")
```

### ❌ Concatenated messages  
```python
logger.error("Failed to process " + object_key + ": " + str(error))
```

### ❌ Inconsistent field names
```python
logger.info("Operation complete", obj_key=key)  # Should be object_key
logger.info("Operation complete", objectKey=key)  # Should be object_key
```

### ❌ Non-serializable values
```python
logger.info("Processing complete", operation="db_query", orm_object=db_obj)  # Objects not serializable
```

## Migration Checklist

When converting existing logging:

- [ ] Replace f-strings with structured key-value pairs
- [ ] Use standard operation names from this document
- [ ] Include timing information for performance-critical operations
- [ ] Add appropriate context fields (user_id, object_key, etc.)
- [ ] Ensure error logs include error_type and error_message
- [ ] Test that all log output is valid JSON in production mode
- [ ] Verify no performance regression from logging changes

## Validation

All logging calls should pass these tests:

1. **JSON Serializable**: All field values must be JSON serializable
2. **Standard Fields**: Use only documented field names
3. **Operation Names**: Follow the hierarchical naming convention
4. **Error Context**: Error logs include error_type and error_message
5. **Performance**: No expensive computations in log statements