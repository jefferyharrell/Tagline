import logging
from typing import Any

from PIL import Image

from app.media_processing.base import MediaProcessor
from app.media_processing.factory import register_processor

logger = logging.getLogger(__name__)


@register_processor
class HEICProcessor(MediaProcessor):
    """Processes HEIC/HEIF images using Pillow and pillow-heif."""

    SUPPORTED_MIMETYPES = {"image/heic", "image/heif"}

    @classmethod
    def handles_mimetype(cls, mimetype: str) -> bool:
        # Normalize the input mimetype
        normalized_mimetype = mimetype.strip().lower()
        # Check against lowercase supported types
        return normalized_mimetype in {
            supported_mimetype.lower() for supported_mimetype in cls.SUPPORTED_MIMETYPES
        }

    async def extract_intrinsic_metadata(self) -> dict[str, Any]:
        """Extracts width, height, mode, and format for HEIC/HEIF."""
        metadata = {}
        try:
            stream = await self.get_content_stream()
            with Image.open(stream) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["mode"] = img.mode
                metadata["format"] = img.format
                logger.debug(
                    f"Extracted HEIC metadata for {self.media_object.object_key}: "
                    f"W={metadata.get('width')}, H={metadata.get('height')}"
                )
        except Exception as e:
            logger.exception(
                f"Pillow/HEIF failed to process {self.media_object.object_key}: {e}"
            )
            return {}
        return metadata
