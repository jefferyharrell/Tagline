import pytest
from pydantic import ValidationError

from app.schemas import MediaObjectMetadata

pytestmark = pytest.mark.unit


def test_valid_metadata_minimal():
    meta = MediaObjectMetadata()
    assert meta.description is None
    assert meta.keywords is None


def test_valid_metadata_full():
    meta = MediaObjectMetadata(
        description="A test description.", keywords=["tag1", "tag2"]
    )
    assert meta.description == "A test description."
    assert meta.keywords == ["tag1", "tag2"]


def test_description_max_length():
    desc = "x" * 1024
    meta = MediaObjectMetadata(description=desc)
    assert meta.description == desc
    with pytest.raises(ValidationError):
        MediaObjectMetadata(description="x" * 1025)


def test_keywords_max_length():
    valid_keyword = "k" * 64
    meta = MediaObjectMetadata(keywords=[valid_keyword])
    assert meta.keywords == [valid_keyword]
    with pytest.raises(ValidationError):
        MediaObjectMetadata(keywords=["k" * 65])


def test_keywords_optional_and_empty():
    meta = MediaObjectMetadata(keywords=None)
    assert meta.keywords is None
    meta2 = MediaObjectMetadata(keywords=[])
    assert meta2.keywords == []


def test_keywords_multiple():
    meta = MediaObjectMetadata(keywords=["foo", "bar", "baz"])
    assert meta.keywords == ["foo", "bar", "baz"]
