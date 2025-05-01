import logging
from abc import abstractmethod
from io import BytesIO
from typing import Any, Protocol, runtime_checkable

from app.config import Settings, get_settings
from app.storage_provider import get_storage_provider
from app.storage_types import MediaObject

logger = logging.getLogger(__name__)


@runtime_checkable
class MediaProcessor(Protocol):
    """Defines the interface for processing different media types."""

    # --- Protocol instance variable declarations --- Required by PEP 544
    media_object: MediaObject
    _content: bytes | None
    _settings: Settings
    # --- End declarations

    @classmethod
    @abstractmethod
    def handles_mimetype(cls, mimetype: str) -> bool:
        """Return True if this processor can handle the given mimetype."""
        raise NotImplementedError

    async def generate_thumbnail(
        self, content: bytes, size: int = 512, fmt: str = "webp", quality: int = 85
    ) -> tuple[bytes, str]:
        """
        Generate a thumbnail from raw image bytes.
        Scales the shortest side to `size` pixels, center-crops to (size, size), converts to RGB, and saves as WebP by default.
        Args:
            content: The raw bytes of the image to thumbnail.
            size: The width/height of the square thumbnail (default: 512).
            fmt: Output format (default: 'webp').
            quality: Output quality (default: 85).
        Returns:
            (thumbnail image bytes, mimetype string)
        """
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(content)) as img:
            img = img.convert("RGB")
            scale = size / min(img.size)
            new_w, new_h = [round(dim * scale) for dim in img.size]
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (img.width - size) // 2
            top = (img.height - size) // 2
            img = img.crop((left, top, left + size, top + size))
            out = BytesIO()
            img.save(out, format=fmt.upper(), quality=quality)
            # Map Pillow format to mimetype
            fmt_lc = fmt.lower()
            mimetype = {
                "jpeg": "image/jpeg",
                "jpg": "image/jpeg",
                "webp": "image/webp",
                "png": "image/png",
                "heic": "image/heic",
                "heif": "image/heif",
            }.get(fmt_lc, f"image/{fmt_lc}")
            return out.getvalue(), mimetype

    def __init__(self, media_object: MediaObject):
        """Initialize with the media object and prepare for content loading."""
        self.media_object = media_object
        self._content = None
        # Store settings if needed by storage provider upon retrieval
        self._settings = get_settings()

    # Changed to async property/method
    async def get_content(self) -> bytes:
        """Lazy-load the media object's content using the storage provider."""
        if self._content is None:
            logger.debug(f"Lazy-loading content for {self.media_object.object_key}")
            try:
                provider = get_storage_provider(self._settings)
                # Use await and the correct method name 'retrieve'
                self._content = await provider.retrieve(self.media_object.object_key)
                if self._content is None:
                    # Should not happen if retrieve raises on failure, but good practice
                    raise ValueError(
                        f"Storage provider returned None content for {self.media_object.object_key}"
                    )
            except Exception:
                logger.exception(
                    f"Failed to retrieve content for {self.media_object.object_key}"
                )
                # Re-raise or handle appropriately
                raise
        return self._content

    # Changed to async property/method
    async def get_content_stream(self) -> BytesIO:
        """Return the content as a BytesIO stream."""
        content_bytes = await self.get_content()
        return BytesIO(content_bytes)

    # Changed to async method
    @abstractmethod
    async def extract_intrinsic_metadata(self) -> dict[str, Any]:
        """Extract format-specific metadata (dimensions, duration, etc.)."""
        raise NotImplementedError

    # Optional methods - can be added later
    # async def generate_previews(self) -> list[str]:
    #     """Generate any previews/thumbnails needed (returns storage paths)."""
    #     return []

    # async def validate(self) -> bool:
    #     """Perform format-specific validation."""
    #     return True
