"""
Singleton storage provider implementation to prevent resource leaks.

This module provides a singleton pattern for storage providers to ensure
we don't create multiple instances that could leak connections over time.
"""

import json
from typing import List, Optional

from app.config import Settings, StorageProviderType
from app.storage_providers.base import StorageProviderBase
from app.storage_providers.dropbox import DropboxStorageProvider
from app.storage_providers.filesystem import FilesystemStorageProvider
from app.structlog_config import get_logger

logger = get_logger(__name__)

# Global storage provider instance
_storage_provider: Optional[StorageProviderBase] = None
_storage_provider_settings_hash: Optional[int] = None


def _get_settings_hash(settings: Settings) -> int:
    """Generate a hash of relevant settings to detect configuration changes."""
    relevant_attrs = [
        settings.STORAGE_PROVIDER,
        (
            settings.FILESYSTEM_ROOT_PATH
            if settings.STORAGE_PROVIDER == StorageProviderType.FILESYSTEM
            else None
        ),
        (
            settings.DROPBOX_ROOT_PATH
            if settings.STORAGE_PROVIDER == StorageProviderType.DROPBOX
            else None
        ),
        (
            settings.DROPBOX_APP_KEY
            if settings.STORAGE_PROVIDER == StorageProviderType.DROPBOX
            else None
        ),
        (
            settings.DROPBOX_APP_SECRET
            if settings.STORAGE_PROVIDER == StorageProviderType.DROPBOX
            else None
        ),
        (
            settings.DROPBOX_REFRESH_TOKEN
            if settings.STORAGE_PROVIDER == StorageProviderType.DROPBOX
            else None
        ),
        settings.PREFIXES_TO_IGNORE,  # Include prefix filtering in hash
    ]
    return hash(tuple(attr for attr in relevant_attrs if attr is not None))


def _parse_prefixes_to_ignore(settings: Settings) -> List[str]:
    """Parse the PREFIXES_TO_IGNORE JSON array from settings."""
    if not settings.PREFIXES_TO_IGNORE:
        return []
    
    try:
        prefixes = json.loads(settings.PREFIXES_TO_IGNORE)
        if not isinstance(prefixes, list):
            logger.error(
                "PREFIXES_TO_IGNORE must be a JSON array",
                operation="parse_prefixes",
                value=settings.PREFIXES_TO_IGNORE,
                error_type="invalid_type"
            )
            return []
        
        # Normalize paths to always start with /
        normalized = []
        for prefix in prefixes:
            if isinstance(prefix, str):
                normalized.append("/" + prefix.lstrip("/"))
            else:
                logger.warning(
                    "Skipping non-string prefix in PREFIXES_TO_IGNORE",
                    operation="parse_prefixes",
                    prefix=prefix,
                    prefix_type=type(prefix).__name__
                )
        
        return normalized
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse PREFIXES_TO_IGNORE as JSON",
            operation="parse_prefixes",
            value=settings.PREFIXES_TO_IGNORE,
            error=str(e),
            error_type="json_decode_error"
        )
        return []


def get_storage_provider_singleton(settings: Settings) -> StorageProviderBase:
    """
    Get or create a singleton storage provider instance.

    This ensures we reuse the same storage provider instance across requests,
    preventing connection/resource leaks that can occur when creating new
    instances for every request.

    The instance is recreated if the configuration changes.
    """
    global _storage_provider, _storage_provider_settings_hash

    current_hash = _get_settings_hash(settings)

    # Check if we need to create a new instance
    if _storage_provider is None or _storage_provider_settings_hash != current_hash:
        if _storage_provider is None:
            logger.info(
                "Creating initial storage provider instance",
                operation="singleton_create",
                provider_type=settings.STORAGE_PROVIDER,
                reason="initial",
            )
        else:
            logger.info(
                "Configuration changed, recreating storage provider instance",
                operation="singleton_create",
                provider_type=settings.STORAGE_PROVIDER,
                reason="config_change",
            )

        provider_type = settings.STORAGE_PROVIDER
        
        # Parse excluded prefixes
        excluded_prefixes = _parse_prefixes_to_ignore(settings)
        if excluded_prefixes:
            logger.info(
                "Storage provider will exclude prefixes",
                operation="singleton_create",
                excluded_prefixes=excluded_prefixes,
                count=len(excluded_prefixes)
            )

        try:
            if provider_type == StorageProviderType.FILESYSTEM:
                assert (
                    settings.FILESYSTEM_ROOT_PATH
                ), "FILESYSTEM_ROOT_PATH must be set for filesystem provider"
                logger.debug(
                    "Creating filesystem storage provider",
                    operation="singleton_create",
                    provider_type="filesystem",
                    root_path=settings.FILESYSTEM_ROOT_PATH,
                    excluded_prefixes_count=len(excluded_prefixes),
                )
                _storage_provider = FilesystemStorageProvider(
                    root_path=settings.FILESYSTEM_ROOT_PATH,
                    excluded_prefixes=excluded_prefixes
                )

            elif provider_type == StorageProviderType.DROPBOX:
                assert (
                    settings.DROPBOX_APP_KEY
                ), "DROPBOX_APP_KEY must be set for dropbox provider"
                assert (
                    settings.DROPBOX_APP_SECRET
                ), "DROPBOX_APP_SECRET must be set for dropbox provider"
                assert (
                    settings.DROPBOX_REFRESH_TOKEN
                ), "DROPBOX_REFRESH_TOKEN must be set for dropbox provider"

                logger.debug(
                    "Creating Dropbox storage provider",
                    operation="singleton_create",
                    provider_type="dropbox",
                    root_path=settings.DROPBOX_ROOT_PATH,
                    excluded_prefixes_count=len(excluded_prefixes),
                )
                _storage_provider = DropboxStorageProvider(
                    root_path=settings.DROPBOX_ROOT_PATH,
                    app_key=settings.DROPBOX_APP_KEY,
                    app_secret=settings.DROPBOX_APP_SECRET,
                    refresh_token=settings.DROPBOX_REFRESH_TOKEN,
                    excluded_prefixes=excluded_prefixes
                )
            else:
                logger.error(
                    "Unknown storage provider type",
                    operation="singleton_create",
                    provider_type=provider_type,
                    error_type="unknown_provider",
                )
                raise NotImplementedError(
                    f"Storage provider '{provider_type}' not implemented"
                )

            _storage_provider_settings_hash = current_hash
            logger.info(
                "Storage provider instance created successfully",
                operation="singleton_create",
                provider_type=provider_type,
                status="success",
            )

        except Exception as e:
            logger.error(
                "Failed to create storage provider instance",
                operation="singleton_create",
                provider_type=provider_type,
                status="failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    else:
        logger.debug(
            "Reusing existing storage provider instance",
            operation="singleton_reuse",
            provider_type=settings.STORAGE_PROVIDER,
        )

    return _storage_provider


def clear_storage_provider_singleton():
    """
    Clear the singleton instance. Useful for testing or forcing recreation.
    """
    global _storage_provider, _storage_provider_settings_hash
    _storage_provider = None
    _storage_provider_settings_hash = None
    logger.info("Storage provider singleton cleared", operation="singleton_clear")
