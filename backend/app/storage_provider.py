from fastapi import Depends

from app.config import Settings, get_settings
from app.storage_provider_singleton import get_storage_provider_singleton
from app.storage_providers.base import StorageProviderBase


class StorageProviderException(Exception):
    """Base exception for storage provider errors."""

    pass


def get_storage_provider(
    settings: Settings = Depends(get_settings),
) -> "StorageProviderBase":
    """
    Factory function to get the configured storage provider instance.

    This now uses a singleton pattern to prevent creating multiple instances
    which can lead to resource leaks over time in production.
    """
    return get_storage_provider_singleton(settings)
