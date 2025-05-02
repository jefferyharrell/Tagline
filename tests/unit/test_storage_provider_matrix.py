import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.storage_providers.base import StorageProviderBase
from app.storage_providers.dropbox import DropboxStorageProvider
from app.storage_providers.filesystem import FilesystemStorageProvider
from app.storage_types import MediaObject

# --- Provider Fixtures ---


@pytest.fixture
def fs_provider_with_files(tmp_path: Path) -> StorageProviderBase:
    """
    FilesystemStorageProvider fixture with a temp directory containing test files.
    Sets the FILESYSTEM_ROOT_PATH env var for the provider.
    """
    # Create test files
    (tmp_path / "foo.txt").write_text("hello")
    (tmp_path / "bar").mkdir(parents=True, exist_ok=True)
    (tmp_path / "bar/baz.txt").write_text("world")
    os.environ["FILESYSTEM_ROOT_PATH"] = str(tmp_path)
    return FilesystemStorageProvider()


@pytest.fixture
def dropbox_provider_with_files(monkeypatch, tmp_path: Path) -> StorageProviderBase:
    """
    DropboxStorageProvider fixture with mocked Dropbox API.
    Simulates two files: /foo.txt with b"hello" and /bar/baz.txt with b"world".
    """
    monkeypatch.setenv("DROPBOX_APP_KEY", "dummy-app-key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "dummy-app-secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "dummy-refresh-token")
    monkeypatch.setenv("DROPBOX_ROOT_PATH", "/test-root")

    from datetime import datetime, timezone

    from dropbox.files import FileMetadata, ListFolderResult

    # Create valid 64-character content hashes (hex strings)
    hash1 = "0" * 64  # Simple valid hash for testing
    hash2 = "1" * 64  # Another simple valid hash for testing

    # Simulate Dropbox file metadata
    file1 = FileMetadata(
        name="foo.txt",
        id="id:1",
        client_modified=datetime.now(timezone.utc),
        server_modified=datetime.now(timezone.utc),
        rev="a1b2c3d4e",
        size=5,
        path_lower="/test-root/foo.txt",
        path_display="/test-root/foo.txt",
        sharing_info=None,
        is_downloadable=True,
        content_hash=hash1,
    )
    file2 = FileMetadata(
        name="baz.txt",
        id="id:2",
        client_modified=datetime.now(timezone.utc),
        server_modified=datetime.now(timezone.utc),
        rev="f5e6d7c8b",
        size=5,
        path_lower="/test-root/bar/baz.txt",
        path_display="/test-root/bar/baz.txt",
        sharing_info=None,
        is_downloadable=True,
        content_hash=hash2,
    )
    entries = [file1, file2]
    list_folder_result = ListFolderResult(
        entries=entries, cursor="cursor", has_more=False
    )

    # Patch Dropbox client methods
    with patch("dropbox.Dropbox") as MockDropbox:
        instance = MockDropbox.return_value

        def files_list_folder_side_effect(path, recursive=True):
            # Simulate Dropbox API prefix filtering
            if path.endswith("/bar") or path.endswith("/bar/"):
                filtered_entries = [file2]
            else:
                filtered_entries = [file1, file2]
            return ListFolderResult(
                entries=filtered_entries, cursor="cursor", has_more=False
            )

        instance.files_list_folder.side_effect = files_list_folder_side_effect
        instance.files_list_folder_continue.return_value = list_folder_result

        # files_download returns (metadata, response)
        def files_download_side_effect(path):
            if path.endswith("foo.txt"):
                return (file1, MagicMock(content=b"hello"))
            elif path.endswith("baz.txt"):
                return (file2, MagicMock(content=b"world"))
            else:
                # Simulate missing file by raising ApiError with .error.get_path().is_not_found() True
                from dropbox.exceptions import ApiError

                class DummyError:
                    def is_path(self):
                        return True

                    def get_path(self):
                        class NotFound:
                            def is_not_found(self):
                                return True

                        return NotFound()

                raise ApiError(
                    request_id="dummy",
                    error=DummyError(),
                    user_message_text=None,
                    user_message_locale=None,
                )

        instance.files_download.side_effect = files_download_side_effect
        provider = DropboxStorageProvider(
            root_path=os.environ["DROPBOX_ROOT_PATH"],
            app_key=os.environ["DROPBOX_APP_KEY"],
            app_secret=os.environ["DROPBOX_APP_SECRET"],
            refresh_token=os.environ["DROPBOX_REFRESH_TOKEN"],
        )
        return provider


# --- Matrix Parametrization ---

provider_fixtures = [
    "fs_provider_with_files",
    "dropbox_provider_with_files",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_fixture", provider_fixtures)
async def test_list_and_retrieve(provider_fixture: str, request: Any):
    provider: StorageProviderBase = request.getfixturevalue(provider_fixture)
    objects = provider.list_media_objects()
    object_keys = {obj.object_key for obj in objects}
    assert object_keys == {"/foo.txt", "/bar/baz.txt"}

    # Verify metadata is present
    for obj in objects:
        assert isinstance(obj, MediaObject)
        assert obj.last_modified is not None
        assert obj.metadata is not None
        assert "size" in obj.metadata

    data = await provider.retrieve("/foo.txt")
    assert data == b"hello"
    data2 = await provider.retrieve("/bar/baz.txt")
    assert data2 == b"world"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_fixture", provider_fixtures)
async def test_list_prefix_and_pagination(provider_fixture: str, request: Any):
    provider: StorageProviderBase = request.getfixturevalue(provider_fixture)
    objects = provider.list_media_objects(prefix="/bar")
    assert len(objects) == 1
    assert objects[0].object_key == "/bar/baz.txt"

    objects = provider.list_media_objects(limit=1)
    assert len(objects) == 1
    objects2 = provider.list_media_objects(offset=1)
    assert len(objects2) == 1
    all_keys = {obj.object_key for obj in objects + objects2}
    assert all_keys == {"/foo.txt", "/bar/baz.txt"}


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_fixture", provider_fixtures)
async def test_list_with_regex(provider_fixture: str, request: Any):
    provider: StorageProviderBase = request.getfixturevalue(provider_fixture)
    objects = provider.list_media_objects(regex=r"\.txt$")
    assert len(objects) == 2
    assert {obj.object_key for obj in objects} == {"/foo.txt", "/bar/baz.txt"}

    objects = provider.list_media_objects(regex=r"foo")
    assert len(objects) == 1
    assert objects[0].object_key == "/foo.txt"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_fixture", provider_fixtures)
async def test_retrieve_missing_raises(provider_fixture: str, request: Any):
    provider: StorageProviderBase = request.getfixturevalue(provider_fixture)
    with pytest.raises(FileNotFoundError):
        await provider.retrieve("/notfound.txt")
