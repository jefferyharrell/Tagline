import io
import logging
from typing import Any

from PIL import Image

from app.media_processing.base import MediaProcessor
from app.media_processing.factory import register_processor
from app.schemas import StoredMediaObject

logger = logging.getLogger(__name__)


@register_processor
class PNGProcessor(MediaProcessor):
    def __init__(self, stored_media_object: StoredMediaObject):
        super().__init__(stored_media_object)

    """Processes PNG images using Pillow."""

    SUPPORTED_MIMETYPES = {"image/png"}

    async def generate_thumbnail(
        self,
        content: bytes,
        size: tuple[int, int] | None = None,
        fmt: str | None = None,
        quality: int | None = None,
    ) -> tuple[bytes, str]:
        """Generate a thumbnail for PNG images using the global or supplied settings."""
        return await super().generate_thumbnail(
            content, size=size, fmt=fmt, quality=quality
        )

    @classmethod
    def handles_mimetype(cls, mimetype: str) -> bool:
        normalized_mimetype = mimetype.strip().lower()
        return normalized_mimetype in {
            supported_mimetype.lower() for supported_mimetype in cls.SUPPORTED_MIMETYPES
        }

    async def extract_intrinsic_metadata(self) -> dict[str, Any]:
        """Extracts width, height, mode, and format from the PNG image."""
        metadata: dict[str, Any] = {}
        try:
            content = await self.get_content()
            with Image.open(io.BytesIO(content)) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["mode"] = img.mode
                metadata["format"] = img.format
                logger.debug(
                    f"Extracted PNG metadata for {self.stored_media_object.object_key}: "
                    f"W={metadata.get('width')}, H={metadata.get('height')}"
                )
        except Exception as e:
            logger.exception(
                f"Pillow failed to process PNG {self.stored_media_object.object_key}: {e}"
            )
            return {}
        return metadata
