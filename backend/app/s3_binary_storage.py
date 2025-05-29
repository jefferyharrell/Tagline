"""S3-compatible storage for derived media files (thumbnails, proxies)."""

import logging
from typing import Generator, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel

logger = logging.getLogger(__name__)


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
                    logger.info(f"Created bucket: {self.config.bucket_name}")
                    self._bucket_initialized = True
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket: {e}")
                raise

    def put_thumbnail(self, media_id: str, data: bytes, content_type: str) -> str:
        """Store thumbnail in S3."""
        return self._put_binary(f"thumbnails/{media_id}", data, content_type)

    def put_proxy(self, media_id: str, data: bytes, content_type: str) -> str:
        """Store proxy in S3."""
        return self._put_binary(f"proxies/{media_id}", data, content_type)

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
            logger.info(f"Stored {key} ({len(data)} bytes)")
            return key
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to store {key}: {e}")
            raise

    def stream_thumbnail(self, media_id: str) -> Generator[bytes, None, None]:
        """Stream thumbnail from S3."""
        return self._stream_binary(f"thumbnails/{media_id}")

    def stream_proxy(self, media_id: str) -> Generator[bytes, None, None]:
        """Stream proxy from S3."""
        return self._stream_binary(f"proxies/{media_id}")

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
                logger.warning(f"Object not found: {key}")
                raise FileNotFoundError(f"Object not found: {key}")
            else:
                logger.error(f"Failed to stream {key}: {e}")
                raise

    def get_thumbnail_metadata(self, media_id: str) -> Optional[dict]:
        """Get thumbnail metadata from S3."""
        return self._get_metadata(f"thumbnails/{media_id}")

    def get_proxy_metadata(self, media_id: str) -> Optional[dict]:
        """Get proxy metadata from S3."""
        return self._get_metadata(f"proxies/{media_id}")

    def _get_metadata(self, key: str) -> Optional[dict]:
        """Get object metadata from S3."""
        try:
            response = self.client.head_object(Bucket=self.config.bucket_name, Key=key)
            return {
                "content_type": response.get("ContentType"),
                "content_length": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            else:
                logger.error(f"Failed to get metadata for {key}: {e}")
                raise

    def delete_binaries(self, media_id: str) -> None:
        """Delete all binaries for a media object."""
        keys_to_delete = [
            f"thumbnails/{media_id}",
            f"proxies/{media_id}",
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
                    logger.error(f"Failed to delete {error['Key']}: {error['Message']}")

        except ClientError as e:
            logger.error(f"Failed to delete binaries for {media_id}: {e}")
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
                logger.error(f"Error checking existence of {key}: {e}")
                raise
