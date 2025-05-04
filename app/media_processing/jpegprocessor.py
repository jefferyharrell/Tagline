import logging
from typing import Any

from PIL import Image

from app.media_processing.base import MediaProcessor
from app.media_processing.factory import register_processor
from app.schemas import StoredMediaObject

logger = logging.getLogger(__name__)


@register_processor
class JPEGProcessor(MediaProcessor):
    def __init__(self, stored_media_object: StoredMediaObject):
        super().__init__(stored_media_object)

    """Processes JPEG images using Pillow."""

    SUPPORTED_MIMETYPES = {"image/jpeg"}

    async def generate_thumbnail(
        self,
        content: bytes,
        size: tuple[int, int] | None = None,
        fmt: str | None = None,
        quality: int | None = None,
    ) -> tuple[bytes, str]:
        """Generate a thumbnail for JPEG images using the global or supplied settings."""
        return await super().generate_thumbnail(
            content, size=size, fmt=fmt, quality=quality
        )

    async def generate_proxy(
        self,
        content: bytes,
        size: tuple[int, int] | None = None,
        fmt: str | None = None,
        quality: int | None = None,
    ) -> tuple[bytes, str]:
        """Generate a proxy for JPEG images using the global or supplied settings."""
        return await super().generate_proxy(
            content, size=size, fmt=fmt, quality=quality
        )

    @classmethod
    def handles_mimetype(cls, mimetype: str) -> bool:
        # Normalize the input mimetype
        normalized_mimetype = mimetype.strip().lower()
        # Check against lowercase supported types
        return normalized_mimetype in {
            supported_mimetype.lower() for supported_mimetype in cls.SUPPORTED_MIMETYPES
        }

    async def extract_intrinsic_metadata(self) -> dict[str, Any]:
        """Extracts width, height, mode, and format using Pillow."""
        metadata = {}
        try:
            stream = await self.get_content_stream()
            with Image.open(stream) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["mode"] = img.mode
                metadata["format"] = img.format
                logger.debug(
                    f"Extracted JPEG metadata for {self.stored_media_object.object_key}: "
                    f"W={metadata.get('width')}, H={metadata.get('height')}"
                )
        except Exception as e:
            logger.exception(
                f"Pillow failed to process JPEG {self.stored_media_object.object_key}: {e}"
            )
            return {}
        return metadata
