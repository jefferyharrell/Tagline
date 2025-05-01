from app.db.repositories.media_object import MediaObjectRepository


def get_media_object_repository() -> MediaObjectRepository:
    """
    Dependency-injected MediaObjectRepository for use in routes and background tasks.
    """
    return MediaObjectRepository()
