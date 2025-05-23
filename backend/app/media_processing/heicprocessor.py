import logging
from io import BytesIO
from typing import Any

from PIL import Image

from app.media_processing.base import MediaProcessor
from app.media_processing.factory import register_processor
from app.schemas import StoredMediaObject

logger = logging.getLogger(__name__)

# Explicitly register pillow-heif plugin for HEIC/HEIF support
try:
    import pillow_heif

    # Disable thumbnails for performance, set quality to default
    pillow_heif.register_heif_opener(thumbnails=False)
    logger.info("pillow-heif: HEIF opener registered successfully without thumbnails.")
except ImportError:
    logger.warning(
        "pillow-heif is not installed; HEIC/HEIF images will not be supported."
    )
except Exception as e:
    logger.error(f"Failed to register pillow-heif HEIF opener: {e}")


@register_processor
class HEICProcessor(MediaProcessor):
    def __init__(self, stored_media_object: StoredMediaObject):
        super().__init__(stored_media_object)

    """Processes HEIC/HEIF images using Pillow and pillow-heif."""

    async def generate_thumbnail(
        self,
        content: bytes,
        size: tuple[int, int] | None = None,
        fmt: str | None = None,
        quality: int | None = None,
    ) -> tuple[bytes, str]:
        """Generate a thumbnail for HEIC images using the default logic, ensuring pillow-heif is registered."""
        logger.debug(
            f"Generating thumbnail for HEIC image, size={size}, fmt={fmt}, quality={quality}"
        )
        # pillow-heif registration should already be handled at module load
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
        """Generate a proxy for HEIC images using the global or supplied settings."""
        return await super().generate_proxy(
            content, size=size, fmt=fmt, quality=quality
        )

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
        stream_content = b""  # Initialize with empty bytes
        try:
            stream = await self.get_content_stream()
            # Ensure the stream is at the beginning
            stream.seek(0)

            # Log the stream details for debugging
            stream_content = stream.read()
            logger.debug(
                f"HEIC stream details for {self.stored_media_object.object_key}: "
                f"Length={len(stream_content)} bytes"
            )

            # Recreate stream after reading
            stream = BytesIO(stream_content)

            with Image.open(stream) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["mode"] = img.mode
                metadata["format"] = img.format
                logger.debug(
                    f"Extracted HEIC metadata for {self.stored_media_object.object_key}: "
                    f"W={metadata.get('width')}, H={metadata.get('height')}"
                )
        except Exception as e:
            logger.exception(
                f"Pillow/HEIF failed to process {self.stored_media_object.object_key}: {e}"
            )
            return {}
        return metadata
