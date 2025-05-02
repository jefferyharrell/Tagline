from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from app.db.repositories.media_object import MediaObjectRepository

router = APIRouter()


@router.get("/media/{id}/thumbnail", response_class=Response, tags=["media"])
def get_media_thumbnail(id: UUID):
    """
    Returns the thumbnail bytes for a media object by UUID, or 404 if not found or no thumbnail exists.
    Always returns as image/jpeg per API spec.
    """
    repo = MediaObjectRepository()
    media_object = repo.get_by_id(id)
    if not media_object or not getattr(media_object, "thumbnail", None):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    mimetype = (
        getattr(media_object, "thumbnail_mimetype", None) or "application/octet-stream"
    )
    return Response(content=media_object.thumbnail, media_type=mimetype)
