# JSON Structured Logging for Tagline Ingest Worker

## Overview

The Tagline ingest worker now uses structured JSON logging to provide better observability and debugging capabilities. All log messages are output as JSON with microsecond-precision timestamps and structured context data.

## JSON Log Format

Each log entry follows this schema:

```json
{
    "timestamp": "2025-06-15T14:30:00.123456Z",
    "level": "INFO",
    "message": "File processed successfully",
    "service": "tagline-ingest-worker",
    "module": "app.tasks.ingest",
    "context": {
        "job_id": "ingest-1234567890-photos-IMG_1234.jpg",
        "file_path": "/photos/IMG_1234.jpg",
        "operation": "thumbnail_generation",
        "duration_ms": 1234.567,
        "function": "ingest",
        "line": 180,
        "file": "ingest.py"
    }
}
```

## Key Features

### 1. Timing Metrics
Every significant operation is timed with millisecond precision:
- Database operations (queries, updates)
- Storage provider operations (file retrieval)
- Media processing (thumbnail/proxy generation)
- S3 operations (upload/registration)
- Redis event publishing

### 2. Contextual Information
Each log entry includes:
- `job_id`: Unique identifier for the ingestion job
- `file_path`: The object key being processed
- `operation`: Specific operation being performed
- Additional context specific to each operation

### 3. Error Tracking
Errors include:
- Full exception message
- Exception type
- Stack trace (for critical errors)
- Operation context when failure occurred

## Implementation Details

### JSON Formatter
Located in `app/json_logging.py`:
- `JSONFormatter`: Custom formatter that outputs JSON
- `ContextLogger`: Wrapper that maintains persistent context
- `setup_json_logging()`: Configuration function

### Worker Setup
The `start_worker.py` script configures JSON logging before starting RQ workers:
```python
python start_worker.py worker-pool ingest -n 8
```

### Usage in Code
```python
from app.json_logging import get_context_logger

logger = get_context_logger(__name__)

# Add persistent context for the job
logger.add_context(
    job_id=job_id,
    file_path=object_key,
    operation="ingest"
)

# Log with additional context
logger.info("Generated thumbnail",
    operation="thumbnail_generation",
    duration_ms=elapsed_ms,
    thumbnail_size=len(thumbnail_bytes)
)
```

## Operations Tracked

### Job Lifecycle
- `job_start`: Ingestion job begins
- `job_complete`: Successful completion with summary
- `job_failed`: Job failed with error details
- `job_critical_failure`: Unrecoverable error

### Database Operations
- `db_update_status`: Status updates with timing
- `db_get_object`: Media object retrieval
- `db_register_thumbnail`: Thumbnail registration
- `db_register_proxy`: Proxy registration

### Media Processing
- `extract_metadata`: Intrinsic metadata extraction
- `get_content`: File content retrieval from storage
- `thumbnail_generation`: Thumbnail creation
- `proxy_generation`: Proxy image creation

### Storage Operations
- `s3_init`: S3 client initialization
- `s3_store_thumbnail`: Thumbnail upload to S3
- `s3_store_proxy`: Proxy upload to S3

### Event Publishing
- `redis_publish`: Redis event publishing with event type

## Log Levels

- **INFO**: Normal operations, timing metrics
- **WARNING**: Non-critical issues (e.g., missing metadata)
- **ERROR**: Operation failures that are recoverable
- **CRITICAL**: System-level failures

## Configuration

Set the log level via environment variable:
```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Querying JSON Logs

### Using jq
```bash
# Filter by operation
docker logs tagline-ingest-worker | jq 'select(.context.operation == "thumbnail_generation")'

# Show slow operations (>1000ms)
docker logs tagline-ingest-worker | jq 'select(.context.duration_ms > 1000)'

# Count errors by type
docker logs tagline-ingest-worker | jq 'select(.level == "ERROR") | .context.error_type' | sort | uniq -c
```

### Log Aggregation
The JSON format is compatible with:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Datadog
- New Relic
- CloudWatch Logs
- Any JSON-aware log aggregation system

## Future Enhancements

1. Add request correlation IDs across services
2. Include memory usage metrics
3. Add distributed tracing support
4. Implement log sampling for high-volume operations
5. Add custom dashboards for common queries