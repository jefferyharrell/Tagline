import logging

from app.db.repositories.media_object import MediaObjectRepository
from app.storage_types import MediaObject

logger = logging.getLogger(__name__)


def ingest(media_object: MediaObject) -> bool:
    # Perform the actual processing for a single media object
    # This could involve downloading, analysis, thumbnail generation, etc.
    logger.info(f"Processing media object: {media_object.object_key}")
    logger.debug(f"  Metadata: {media_object.metadata}")
    logger.debug(f"  Last modified: {media_object.last_modified}")

    # Use repository to commit to database
    repo = MediaObjectRepository()
    db_obj = repo.create(media_object)

    if not db_obj:
        logger.error(
            f"Failed to commit MediaObject via repository for key: {media_object.object_key}"
        )
        # Decide if this should be a task failure
        return False  # Indicate failure

    # Return success to indicate the task completed
    return True
