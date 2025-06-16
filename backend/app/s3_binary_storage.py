"""S3-compatible storage for derived media files (thumbnails, proxies)."""

from typing import Generator, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel

from app.structlog_config import get_logger

logger = get_logger(__name__)


class S3Config(BaseModel):
    """Configuration for S3 binary storage."""

    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    region: str = "us-east-1"

    # Streaming configuration
    chunk_size: int = 8192  # 8KB chunks for streaming

    # Connection pooling
    max_pool_connections: int = 10


class S3BinaryStorage:
    """Storage service for derived media files in S3-compatible object storage."""

    def __init__(self, config: S3Config):
        self.config = config
        self._client = None
        self._bucket_initialized = False

    @property
    def client(self):
        """Lazy initialization of S3 client with connection pooling."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.config.endpoint_url,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                region_name=self.config.region,
                config=Config(max_pool_connections=self.config.max_pool_connections),
            )
        return self._client

    def _ensure_bucket(self) -> None:
        """Ensure the bucket exists, create if it doesn't."""
        if self._bucket_initialized:
            return

        try:
            self.client.head_bucket(Bucket=self.config.bucket_name)
            self._bucket_initialized = True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # Bucket doesn't exist, create it
                try:
                    self.client.create_bucket(Bucket=self.config.bucket_name)
                    logger.info(
                        "Created S3 bucket",
                        provider_type="s3",
                        operation="ensure_bucket",
                        bucket_name=self.config.bucket_name,
                    )
                    self._bucket_initialized = True
                except ClientError as create_error:
                    logger.error(
                        "Failed to create S3 bucket",
                        provider_type="s3",
                        operation="ensure_bucket",
                        error_type="create_failed",
                        bucket_name=self.config.bucket_name,
                        error=str(create_error),
                    )
                    raise
            else:
                logger.error(
                    "Error checking S3 bucket",
                    provider_type="s3",
                    operation="ensure_bucket",
                    error_type="check_failed",
                    bucket_name=self.config.bucket_name,
                    error=str(e),
                )
                raise

    def put_thumbnail(self, object_key: str, data: bytes, content_type: str) -> str:
        """Store thumbnail in S3."""
        clean_key = object_key.lstrip("/")
        return self._put_binary(f"thumbnails/{clean_key}.jpg", data, content_type)

    def put_proxy(self, object_key: str, data: bytes, content_type: str) -> str:
        """Store proxy in S3."""
        clean_key = object_key.lstrip("/")
        return self._put_binary(f"proxies/{clean_key}.jpg", data, content_type)

    def _put_binary(self, key: str, data: bytes, content_type: str) -> str:
        """Store binary data in S3."""
        self._ensure_bucket()

        try:
            self.client.put_object(
                Bucket=self.config.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            logger.info(
                "Stored binary data in S3",
                provider_type="s3",
                operation="put_binary",
                s3_key=key,
                data_size=len(data),
                content_type=content_type,
                bucket_name=self.config.bucket_name,
            )
            return key
        except (ClientError, NoCredentialsError) as e:
            logger.error(
                "Failed to store binary data in S3",
                provider_type="s3",
                operation="put_binary",
                error_type="store_failed",
                s3_key=key,
                bucket_name=self.config.bucket_name,
                error=str(e),
            )
            raise

    def stream_thumbnail(self, object_key: str) -> Generator[bytes, None, None]:
        """Stream thumbnail from S3."""
        clean_key = object_key.lstrip("/")
        return self._stream_binary(f"thumbnails/{clean_key}.jpg")

    def stream_proxy(self, object_key: str) -> Generator[bytes, None, None]:
        """Stream proxy from S3."""
        clean_key = object_key.lstrip("/")
        return self._stream_binary(f"proxies/{clean_key}.jpg")

    def _stream_binary(self, key: str) -> Generator[bytes, None, None]:
        """Stream binary data from S3 in chunks."""
        try:
            response = self.client.get_object(Bucket=self.config.bucket_name, Key=key)

            # Stream the body in chunks
            body = response["Body"]
            while True:
                chunk = body.read(self.config.chunk_size)
                if not chunk:
                    break
                yield chunk

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(
                    "S3 object not found for streaming",
                    provider_type="s3",
                    operation="stream_binary",
                    error_type="not_found",
                    s3_key=key,
                    bucket_name=self.config.bucket_name,
                )
                raise FileNotFoundError(f"Object not found: {key}")
            else:
                logger.error(
                    "Failed to stream S3 object",
                    provider_type="s3",
                    operation="stream_binary",
                    error_type="stream_failed",
                    s3_key=key,
                    bucket_name=self.config.bucket_name,
                    error=str(e),
                )
                raise

    def get_thumbnail_metadata(self, object_key: str) -> Optional[dict]:
        """Get thumbnail metadata from S3."""
        clean_key = object_key.lstrip("/")
        s3_key = f"thumbnails/{clean_key}.jpg"
        logger.info(
            "Getting thumbnail metadata",
            provider_type="s3",
            operation="get_thumbnail_metadata",
            object_key=object_key,
            s3_key=s3_key,
        )
        return self._get_metadata(s3_key)

    def get_proxy_metadata(self, object_key: str) -> Optional[dict]:
        """Get proxy metadata from S3."""
        clean_key = object_key.lstrip("/")
        return self._get_metadata(f"proxies/{clean_key}.jpg")

    def _get_metadata(self, key: str) -> Optional[dict]:
        """Get object metadata from S3."""
        try:
            logger.info(
                "Attempting to get S3 metadata",
                provider_type="s3",
                operation="get_metadata",
                s3_key=key,
                bucket_name=self.config.bucket_name,
            )
            response = self.client.head_object(Bucket=self.config.bucket_name, Key=key)
            logger.info(
                "Successfully got S3 metadata",
                provider_type="s3",
                operation="get_metadata",
                s3_key=key,
                bucket_name=self.config.bucket_name,
            )
            return {
                "content_type": response.get("ContentType"),
                "content_length": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.warning(
                    "S3 object not found for metadata",
                    provider_type="s3",
                    operation="get_metadata",
                    error_type="not_found",
                    s3_key=key,
                    bucket_name=self.config.bucket_name,
                )
                return None
            else:
                logger.error(
                    "Failed to get S3 metadata",
                    provider_type="s3",
                    operation="get_metadata",
                    error_type="metadata_failed",
                    s3_key=key,
                    bucket_name=self.config.bucket_name,
                    error=str(e),
                )
                raise

    def delete_binaries(self, object_key: str) -> None:
        """Delete all binaries for a media object."""
        clean_key = object_key.lstrip("/")
        keys_to_delete = [
            f"thumbnails/{clean_key}.jpg",
            f"proxies/{clean_key}.jpg",
        ]

        # S3 delete_objects is more efficient for multiple deletes
        try:
            response = self.client.delete_objects(
                Bucket=self.config.bucket_name,
                Delete={
                    "Objects": [{"Key": key} for key in keys_to_delete],
                    "Quiet": True,  # Only report errors
                },
            )

            if "Errors" in response:
                for error in response["Errors"]:
                    logger.error(
                        "Failed to delete S3 object",
                        provider_type="s3",
                        operation="delete_binaries",
                        error_type="delete_failed",
                        s3_key=error["Key"],
                        error_message=error["Message"],
                    )

        except ClientError as e:
            logger.error(
                "Failed to delete binaries for object",
                provider_type="s3",
                operation="delete_binaries",
                error_type="delete_batch_failed",
                object_key=object_key,
                bucket_name=self.config.bucket_name,
                error=str(e),
            )
            raise

    def exists(self, key: str) -> bool:
        """Check if an object exists in S3."""
        try:
            self.client.head_object(Bucket=self.config.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                logger.error(
                    "Error checking S3 object existence",
                    provider_type="s3",
                    operation="exists",
                    error_type="existence_check_failed",
                    s3_key=key,
                    bucket_name=self.config.bucket_name,
                    error=str(e),
                )
                raise
