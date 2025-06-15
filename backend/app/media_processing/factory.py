import logging
import mimetypes
from typing import Set, Type

from app.media_processing.base import MediaProcessor
from app.schemas import StoredMediaObject

logger = logging.getLogger(__name__)

# Simple set-based registry for now. Could evolve into a class
# with priority support, etc.
_PROCESSOR_REGISTRY: set[Type[MediaProcessor]] = set()


def register_processor(processor_cls: Type[MediaProcessor]):
    """Registers a media processor class. Can be used as a decorator."""
    logger.debug(
        "Registering media processor",
        operation="register_processor",
        processor_class=processor_cls.__name__
    )
    _PROCESSOR_REGISTRY.add(processor_cls)
    return processor_cls


def is_mimetype_supported(mimetype: str) -> bool:
    """Check if a given MIME type is supported by any registered processor."""
    # Ensure processors are loaded before checking
    _ensure_processors_loaded()

    logger.debug(
        "Checking mimetype support",
        operation="is_mimetype_supported",
        mimetype=mimetype
    )
    logger.debug(
        "Current processor registry",
        operation="is_mimetype_supported",
        registry_size=len(_PROCESSOR_REGISTRY),
        processors=[cls.__name__ for cls in _PROCESSOR_REGISTRY]
    )
    supported = any(
        processor_cls.handles_mimetype(mimetype)
        for processor_cls in _PROCESSOR_REGISTRY
    )
    logger.debug(
        "Mimetype support check result",
        operation="is_mimetype_supported",
        mimetype=mimetype,
        supported=supported
    )
    return supported


def get_supported_extensions() -> Set[str]:
    """Get all file extensions supported by registered processors.

    Returns:
        Set of lowercase file extensions (e.g., {'.jpg', '.png', '.heic'})
    """
    # Ensure processors are loaded before checking
    _ensure_processors_loaded()

    supported_extensions = set()

    # Common extension to MIME type mappings for media files
    # This covers the most common cases and can be extended as needed
    extension_to_mimetype = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".heic": "image/heic",
        ".heif": "image/heif",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".m4v": "video/x-m4v",
        ".3gp": "video/3gpp",
        ".wmv": "video/x-ms-wmv",
    }

    # Check each known extension against registered processors
    for ext, mimetype in extension_to_mimetype.items():
        if is_mimetype_supported(mimetype):
            supported_extensions.add(ext)

    # Also use Python's mimetypes module for additional extensions
    # This helps catch any extensions we might have missed
    for processor_cls in _PROCESSOR_REGISTRY:
        if hasattr(processor_cls, "SUPPORTED_MIMETYPES"):
            supported_mimetypes = getattr(processor_cls, "SUPPORTED_MIMETYPES", set())
            for mimetype in supported_mimetypes:
                # Use mimetypes.guess_all_extensions to find extensions for this MIME type
                extensions = mimetypes.guess_all_extensions(mimetype)
                if extensions:
                    supported_extensions.update(ext.lower() for ext in extensions)

    logger.debug(
        "Dynamically determined supported extensions",
        operation="get_supported_extensions",
        extensions=sorted(supported_extensions),
        extension_count=len(supported_extensions)
    )
    return supported_extensions


def is_extension_supported(file_extension: str) -> bool:
    """Check if a file extension is supported by any registered processor.

    Args:
        file_extension: File extension (with or without leading dot, case insensitive)

    Returns:
        True if the extension is supported, False otherwise
    """
    # Normalize the extension
    if not file_extension.startswith("."):
        file_extension = "." + file_extension
    file_extension = file_extension.lower()

    return file_extension in get_supported_extensions()


def _ensure_processors_loaded():
    """Lazily load processor modules to avoid heavy imports at worker startup."""
    if len(_PROCESSOR_REGISTRY) == 0:
        logger.debug(
            "Lazy-loading media processors",
            operation="_ensure_processors_loaded"
        )
        # Import processor modules here to trigger registration
        try:
            from app.media_processing import jpegprocessor  # noqa: F401

            logger.debug(
                "Loaded processor module",
                operation="_ensure_processors_loaded",
                processor_type="jpeg"
            )
        except ImportError as e:
            logger.warning(
                "Failed to load processor module",
                operation="_ensure_processors_loaded",
                processor_type="jpeg",
                error=str(e),
                error_type=type(e).__name__
            )

        try:
            from app.media_processing import heicprocessor  # noqa: F401

            logger.debug(
                "Loaded processor module",
                operation="_ensure_processors_loaded",
                processor_type="heic"
            )
        except ImportError as e:
            logger.warning(
                "Failed to load processor module",
                operation="_ensure_processors_loaded",
                processor_type="heic",
                error=str(e),
                error_type=type(e).__name__
            )

        try:
            from app.media_processing import pngprocessor  # noqa: F401

            logger.debug(
                "Loaded processor module",
                operation="_ensure_processors_loaded",
                processor_type="png"
            )
        except ImportError as e:
            logger.warning(
                "Failed to load processor module",
                operation="_ensure_processors_loaded",
                processor_type="png",
                error=str(e),
                error_type=type(e).__name__
            )

        logger.info(
            "Lazy-loaded media processors",
            operation="_ensure_processors_loaded",
            loaded_count=len(_PROCESSOR_REGISTRY)
        )


def get_processor(stored_media_object: StoredMediaObject) -> MediaProcessor:
    """Finds and instantiates the appropriate processor for the media object."""
    mimetype = (stored_media_object.metadata or {}).get("mimetype")
    if not mimetype:
        # Maybe raise a specific exception type?
        raise ValueError(
            f"Media object {stored_media_object.object_key} missing mimetype"
        )

    # Ensure processors are loaded before checking registry
    _ensure_processors_loaded()

    applicable_processors = [
        p_cls for p_cls in _PROCESSOR_REGISTRY if p_cls.handles_mimetype(mimetype)
    ]

    if not applicable_processors:
        logger.warning(
            "No registered processor found for mimetype",
            operation="get_processor",
            mimetype=mimetype,
            available_processors=[cls.__name__ for cls in _PROCESSOR_REGISTRY]
        )
        raise NotImplementedError(f"No processor registered for mimetype: {mimetype}")

    # For now, just take the first one. Add priority later if needed.
    processor_cls = applicable_processors[0]
    if len(applicable_processors) > 1:
        logger.warning(
            "Multiple processors found for mimetype, using first one",
            operation="get_processor",
            mimetype=mimetype,
            applicable_processors=[cls.__name__ for cls in applicable_processors],
            selected_processor=processor_cls.__name__
        )

    logger.debug(
        "Using processor for mimetype",
        operation="get_processor",
        processor_class=processor_cls.__name__,
        mimetype=mimetype
    )
    try:
        # Pass the media object to the constructor
        return processor_cls(stored_media_object)
    except Exception as e:
        logger.exception(
            "Failed to instantiate processor",
            operation="get_processor",
            processor_class=processor_cls.__name__,
            object_key=stored_media_object.object_key,
            mimetype=mimetype
        )
        # Re-raise a more specific error?
        raise RuntimeError(f"Processor instantiation failed for {mimetype}") from e
