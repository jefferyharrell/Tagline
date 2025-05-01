import logging
from typing import Type

from app.media_processing.base import MediaProcessor
from app.storage_types import MediaObject

logger = logging.getLogger(__name__)

# Simple set-based registry for now. Could evolve into a class
# with priority support, etc.
_PROCESSOR_REGISTRY: set[Type[MediaProcessor]] = set()


def register_processor(processor_cls: Type[MediaProcessor]):
    """Registers a media processor class. Can be used as a decorator."""
    logger.debug(f"Registering processor: {processor_cls.__name__}")
    _PROCESSOR_REGISTRY.add(processor_cls)
    return processor_cls


def is_mimetype_supported(mimetype: str) -> bool:
    """Check if a given MIME type is supported by any registered processor."""
    logger.debug(f"Checking if mimetype '{mimetype}' is supported.")
    logger.debug(f"Current registry: {_PROCESSOR_REGISTRY}")
    supported = any(
        processor_cls.handles_mimetype(mimetype)
        for processor_cls in _PROCESSOR_REGISTRY
    )
    logger.debug(f"Mimetype '{mimetype}' supported: {supported}")
    return supported


def get_processor(media_object: MediaObject) -> MediaProcessor:
    """Finds and instantiates the appropriate processor for the media object."""
    mimetype = (media_object.metadata or {}).get("mimetype")
    if not mimetype:
        # Maybe raise a specific exception type?
        raise ValueError(f"Media object {media_object.object_key} missing mimetype")

    applicable_processors = [
        p_cls for p_cls in _PROCESSOR_REGISTRY if p_cls.handles_mimetype(mimetype)
    ]

    if not applicable_processors:
        logger.warning(f"No registered processor found for mimetype: {mimetype}")
        raise NotImplementedError(f"No processor registered for mimetype: {mimetype}")

    # For now, just take the first one. Add priority later if needed.
    processor_cls = applicable_processors[0]
    if len(applicable_processors) > 1:
        logger.warning(
            f"Multiple processors found for {mimetype}: {applicable_processors}. Using {processor_cls.__name__}."
        )

    logger.debug(f"Using processor {processor_cls.__name__} for mimetype {mimetype}")
    try:
        # Pass the media object to the constructor
        return processor_cls(media_object)
    except Exception as e:
        logger.exception(
            f"Failed to instantiate processor {processor_cls.__name__} "
            f"for {media_object.object_key}"
        )
        # Re-raise a more specific error?
        raise RuntimeError(f"Processor instantiation failed for {mimetype}") from e
