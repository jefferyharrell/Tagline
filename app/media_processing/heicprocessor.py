import logging
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from app.media_processing.base import MediaProcessor
from app.media_processing.factory import register_processor

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
        stream_content = b""  # Initialize with empty bytes
        try:
            stream = await self.get_content_stream()
            # Ensure the stream is at the beginning
            stream.seek(0)

            # Log the stream details for debugging
            stream_content = stream.read()
            logger.debug(
                f"HEIC stream details for {self.media_object.object_key}: "
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
                    f"Extracted HEIC metadata for {self.media_object.object_key}: "
                    f"W={metadata.get('width')}, H={metadata.get('height')}"
                )
        except Exception as e:
            logger.exception(
                f"Pillow/HEIF failed to process {self.media_object.object_key}: {e}"
            )
            # If possible, save the problematic file for investigation
            try:
                error_dir = Path("/tmp/heic_errors")
                error_dir.mkdir(parents=True, exist_ok=True)
                # Clean the object key to create a safe filename
                safe_key = self.media_object.object_key.replace("/", "_").lstrip("_")
                p = Path(safe_key)
                # Use stem and suffix to reconstruct filename correctly
                filename = f"{p.stem}{p.suffix}" if p.suffix else p.stem
                error_file = error_dir / filename
                with open(error_file, "wb") as f:
                    f.write(stream_content)
                logger.warning(f"Saved problematic HEIC file to {error_file}")
            except Exception as save_error:
                logger.error(f"Could not save problematic HEIC file: {save_error}")

            return {}
        return metadata
