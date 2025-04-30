import os
from pathlib import Path
from typing import Any

import pytest

from app.filesystem_storage_provider import FilesystemStorageProvider
from app.storage_provider import StorageProviderBase

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


# --- Matrix Parametrization ---

provider_fixtures = [
    "fs_provider_with_files",
    # Add more provider fixture names here as you implement them
]


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_fixture", provider_fixtures)
async def test_list_and_retrieve(provider_fixture: str, request: Any):
    provider: StorageProviderBase = request.getfixturevalue(provider_fixture)
    keys = await provider.list()
    assert set(keys) == {"/foo.txt", "/bar/baz.txt"}
    data = await provider.retrieve("/foo.txt")
    assert data == b"hello"
    data2 = await provider.retrieve("/bar/baz.txt")
    assert data2 == b"world"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_fixture", provider_fixtures)
async def test_list_prefix_and_pagination(provider_fixture: str, request: Any):
    provider: StorageProviderBase = request.getfixturevalue(provider_fixture)
    # Prefix
    keys = await provider.list(prefix="/bar")
    assert keys == ["/bar/baz.txt"]
    # Pagination
    keys = await provider.list(limit=1)
    assert len(keys) == 1
    keys2 = await provider.list(offset=1)
    assert len(keys2) == 1
    assert set(keys + keys2) == {"/foo.txt", "/bar/baz.txt"}


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_fixture", provider_fixtures)
async def test_retrieve_missing_raises(provider_fixture: str, request: Any):
    provider: StorageProviderBase = request.getfixturevalue(provider_fixture)
    with pytest.raises(FileNotFoundError):
        await provider.retrieve("/notfound.txt")
