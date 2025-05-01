from app.config import Settings, StorageProviderType
from app.dropbox_storage_provider import DropboxStorageProvider
from app.filesystem_storage_provider import FilesystemStorageProvider
from app.storage_types import StorageProviderBase


class StorageProviderException(Exception):
    """Base exception for storage provider errors."""

    pass


def get_storage_provider(settings: Settings) -> "StorageProviderBase":
    """Factory function to get the configured storage provider instance."""
    provider_type = settings.STORAGE_PROVIDER

    if provider_type == StorageProviderType.FILESYSTEM:
        assert (
            settings.FILESYSTEM_ROOT_PATH
        ), "FILESYSTEM_ROOT_PATH must be set for filesystem provider"
        return FilesystemStorageProvider(root_path=settings.FILESYSTEM_ROOT_PATH)
    elif provider_type == StorageProviderType.DROPBOX:
        assert (
            settings.DROPBOX_ROOT_PATH
        ), "DROPBOX_ROOT_PATH must be set for dropbox provider"
        assert (
            settings.DROPBOX_APP_KEY
        ), "DROPBOX_APP_KEY must be set for dropbox provider"
        assert (
            settings.DROPBOX_APP_SECRET
        ), "DROPBOX_APP_SECRET must be set for dropbox provider"
        assert (
            settings.DROPBOX_REFRESH_TOKEN
        ), "DROPBOX_REFRESH_TOKEN must be set for dropbox provider"
        return DropboxStorageProvider(
            root_path=settings.DROPBOX_ROOT_PATH,
            app_key=settings.DROPBOX_APP_KEY,
            app_secret=settings.DROPBOX_APP_SECRET,
            refresh_token=settings.DROPBOX_REFRESH_TOKEN,
        )
    # Add other providers here as elif blocks
    else:
        # This case should ideally be prevented by Pydantic validation
        raise NotImplementedError(f"Storage provider '{provider_type}' not implemented")
