import logging
from abc import abstractmethod
from io import BytesIO
from typing import Any, Protocol, runtime_checkable

from app.config import Settings, get_settings
from app.schemas import StoredMediaObject
from app.storage_provider import get_storage_provider

logger = logging.getLogger(__name__)


@runtime_checkable
class MediaProcessor(Protocol):
    """Defines the interface for processing different media types."""

    # --- Protocol instance variable declarations --- Required by PEP 544
    stored_media_object: StoredMediaObject
    _content: bytes | None
    _settings: Settings
    # --- End declarations

    @classmethod
    @abstractmethod
    def handles_mimetype(cls, mimetype: str) -> bool:
        """Return True if this processor can handle the given mimetype."""
        raise NotImplementedError

    async def generate_thumbnail(
        self,
        content: bytes,
        size: tuple[int, int] | None = None,
        fmt: str | None = None,
        quality: int | None = None,
    ) -> tuple[bytes, str]:
        """
        Generate a thumbnail from raw image bytes using global or supplied settings.
        If not provided, uses settings.THUMBNAIL_SIZE, settings.THUMBNAIL_FORMAT, and settings.THUMBNAIL_QUALITY.
        Resizes to the specified width and height, converts to RGB, and saves as the configured format.
        Returns:
            (thumbnail image bytes, mimetype string)
        """
        from app.config import get_settings

        settings = get_settings()
        size = size if size is not None else settings.THUMBNAIL_SIZE
        fmt = fmt if fmt is not None else settings.THUMBNAIL_FORMAT
        quality = quality if quality is not None else settings.THUMBNAIL_QUALITY
        from io import BytesIO

        from PIL import Image, ImageOps

        width, height = size
        content_stream = BytesIO(content)
        try:
            with Image.open(content_stream) as img:
                # Apply EXIF orientation correction before any other processing
                img = ImageOps.exif_transpose(img)
                img = img.convert("RGB")
                orig_w, orig_h = img.size
                # If image is smaller than or equal to thumbnail size, do not resize
                if orig_w <= width and orig_h <= height:
                    thumb = img.copy()  # Create a copy since original will be closed
                else:
                    # Scale so that the smallest dimension fits within the thumbnail size
                    scale = max(width / orig_w, height / orig_h)
                    new_w = int(orig_w * scale)
                    new_h = int(orig_h * scale)
                    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    # Center crop to the thumbnail size
                    left = (new_w - width) // 2
                    top = (new_h - height) // 2
                    right = left + width
                    bottom = top + height
                    thumb = resized.crop((left, top, right, bottom))
                    resized.close()  # Explicitly close intermediate image

                out = BytesIO()
                thumb.save(out, format=fmt.upper(), quality=quality)
                thumb.close()  # Explicitly close thumbnail image

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
        finally:
            content_stream.close()

    async def generate_proxy(
        self,
        content: bytes,
        size: tuple[int, int] | None = None,
        fmt: str | None = None,
        quality: int | None = None,
    ) -> tuple[bytes, str]:
        """
        Generate a proxy from raw image bytes using global or supplied settings.
        If not provided, uses settings.PROXY_SIZE, settings.PROXY_FORMAT, and settings.PROXY_QUALITY.
        Resizes to the specified width and height while maintaining aspect ratio, converts to RGB,
        and saves as the configured format.
        Returns:
            (proxy image bytes, mimetype string)
        """
        from app.config import get_settings

        settings = get_settings()
        size = size if size is not None else settings.PROXY_SIZE
        fmt = fmt if fmt is not None else settings.PROXY_FORMAT
        quality = quality if quality is not None else settings.PROXY_QUALITY

        from io import BytesIO

        from PIL import Image, ImageOps

        width, height = size
        content_stream = BytesIO(content)
        try:
            with Image.open(content_stream) as img:
                # Apply EXIF orientation correction before any other processing
                img = ImageOps.exif_transpose(img)
                img = img.convert("RGB")
                orig_w, orig_h = img.size

                # If image is smaller than proxy size, do not resize
                if orig_w <= width and orig_h <= height:
                    proxy = img.copy()  # Create a copy since original will be closed
                else:
                    # Calculate new dimensions while maintaining aspect ratio
                    ratio = min(width / orig_w, height / orig_h)
                    new_w = int(orig_w * ratio)
                    new_h = int(orig_h * ratio)
                    proxy = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                out = BytesIO()
                proxy.save(out, format=fmt.upper(), quality=quality)
                proxy.close()  # Explicitly close proxy image

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
        finally:
            content_stream.close()

    def __init__(self, stored_media_object: StoredMediaObject):
        """Initialize with the stored media object and prepare for content loading."""
        self.stored_media_object = stored_media_object
        self._content = None
        # Store settings if needed by storage provider upon retrieval
        self._settings = get_settings()

    # Changed to async property/method
    async def get_content(self) -> bytes:
        """Lazy-load the stored media object's content using the storage provider."""
        if self._content is None:
            logger.debug(
                f"Lazy-loading content for {self.stored_media_object.object_key}"
            )
            try:
                provider = get_storage_provider(self._settings)
                # Use await and the correct method name 'retrieve'
                self._content = await provider.retrieve(
                    self.stored_media_object.object_key
                )
                if self._content is None:
                    # Should not happen if retrieve raises on failure, but good practice
                    raise ValueError(
                        f"Storage provider returned None content for {self.stored_media_object.object_key}"
                    )
            except Exception:
                logger.exception(
                    f"Failed to retrieve content for {self.stored_media_object.object_key}"
                )
                # Re-raise or handle appropriately
                raise
        return self._content

    # Changed to async property/method
    async def get_content_stream(self) -> BytesIO:
        """Return the content as a BytesIO stream."""
        content_bytes = await self.get_content()
        return BytesIO(content_bytes)

    def clear_content_cache(self) -> None:
        """Clear the cached content to free memory."""
        if self._content is not None:
            logger.debug(
                f"Clearing content cache for {self.stored_media_object.object_key}"
            )
            self._content = None

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
