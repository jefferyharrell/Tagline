"""Move detection service for identifying when files have been moved."""

import time
from datetime import datetime
from typing import List, Optional

from app.db.repositories.media_object import MediaObjectRepository
from app.domain_media_object import MediaObjectRecord
from app.schemas import StoredMediaObject
from app.storage_providers.base import StorageProviderBase
from app.structlog_config import get_logger
from app.utils.hashing import compute_content_hash_sync

logger = get_logger(__name__)


class MoveDetectionResult:
    """Result of move detection analysis."""
    
    def __init__(
        self,
        action: str,  # "create_new", "move", "copy" 
        existing_record: Optional[MediaObjectRecord] = None,
        reason: str = "",
        confidence: float = 0.0
    ):
        self.action = action
        self.existing_record = existing_record
        self.reason = reason
        self.confidence = confidence


class MoveDetectionService:
    """Service for detecting file moves using metadata-first approach."""
    
    def __init__(
        self, 
        storage_provider: StorageProviderBase,
        media_repo: MediaObjectRepository
    ):
        self.storage_provider = storage_provider
        self.media_repo = media_repo
        
    async def analyze_file(self, stored_obj: StoredMediaObject) -> MoveDetectionResult:
        """Analyze a discovered file to determine if it's new, moved, or copied.
        
        Args:
            stored_obj: File discovered by storage provider
            
        Returns:
            MoveDetectionResult indicating what action to take
        """
        start_time = time.time()
        
        logger.info(
            "Starting move detection analysis",
            operation="analyze_file",
            object_key=stored_obj.object_key,
            file_id=stored_obj.file_id
        )
        
        try:
            # Step 1: Check if file already exists at current path
            existing = self.media_repo.get_by_object_key(stored_obj.object_key)
            if existing:
                duration_ms = (time.time() - start_time) * 1000
                logger.debug(
                    "File already exists at current path",
                    operation="analyze_file",
                    object_key=stored_obj.object_key,
                    duration_ms=duration_ms
                )
                return MoveDetectionResult(
                    action="create_new",
                    reason="File already exists at this path",
                    confidence=1.0
                )
            
            # Step 2: Quick check using provider file ID (if available)
            if stored_obj.file_id and hasattr(self.storage_provider, 'provider_name'):
                match = self.media_repo.find_by_provider_file_id(stored_obj.file_id)
                if match:
                    # Same file ID at different path = move
                    is_move = await self._verify_move_vs_copy(match, stored_obj)
                    if is_move:
                        duration_ms = (time.time() - start_time) * 1000
                        logger.info(
                            "Move detected via provider file ID",
                            operation="analyze_file",
                            object_key=stored_obj.object_key,
                            old_object_key=match.object_key,
                            provider_file_id=stored_obj.file_id,
                            duration_ms=duration_ms
                        )
                        return MoveDetectionResult(
                            action="move",
                            existing_record=match,
                            reason="Same provider file ID at different path",
                            confidence=0.95
                        )
                    else:
                        duration_ms = (time.time() - start_time) * 1000
                        logger.info(
                            "Copy detected via provider file ID",
                            operation="analyze_file",
                            object_key=stored_obj.object_key,
                            original_object_key=match.object_key,
                            provider_file_id=stored_obj.file_id,
                            duration_ms=duration_ms
                        )
                        return MoveDetectionResult(
                            action="create_new",
                            reason="Same provider file ID but original still exists (copy)",
                            confidence=0.95
                        )
            
            # Step 3: Fingerprint matching (size + modified time)
            file_size = stored_obj.metadata.get('size') if stored_obj.metadata else None
            if file_size:
                file_modified = None
                if stored_obj.last_modified:
                    try:
                        file_modified = datetime.fromisoformat(
                            stored_obj.last_modified.replace('Z', '+00:00')
                        )
                    except ValueError:
                        pass
                
                candidates = self.media_repo.find_by_fingerprint(file_size, file_modified)
                if candidates:
                    logger.debug(
                        "Found fingerprint candidates",
                        operation="analyze_file",
                        object_key=stored_obj.object_key,
                        candidates_count=len(candidates),
                        file_size=file_size,
                        file_modified=file_modified.isoformat() if file_modified else None
                    )
                    
                    # Step 4: Content hash verification for best candidate
                    best_match = await self._verify_with_content_hash(stored_obj, candidates)
                    if best_match:
                        is_move = await self._verify_move_vs_copy(best_match, stored_obj)
                        if is_move:
                            duration_ms = (time.time() - start_time) * 1000
                            logger.info(
                                "Move detected via content hash",
                                operation="analyze_file",
                                object_key=stored_obj.object_key,
                                old_object_key=best_match.object_key,
                                duration_ms=duration_ms
                            )
                            return MoveDetectionResult(
                                action="move",
                                existing_record=best_match,
                                reason="Same content hash and original no longer exists",
                                confidence=0.9
                            )
                        else:
                            duration_ms = (time.time() - start_time) * 1000
                            logger.info(
                                "Copy detected via content hash",
                                operation="analyze_file",
                                object_key=stored_obj.object_key,
                                original_object_key=best_match.object_key,
                                duration_ms=duration_ms
                            )
                            return MoveDetectionResult(
                                action="create_new",
                                reason="Same content hash but original still exists (copy)",
                                confidence=0.9
                            )
            
            # Step 5: No match found - create new
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "No match found - treating as new file",
                operation="analyze_file",
                object_key=stored_obj.object_key,
                duration_ms=duration_ms
            )
            return MoveDetectionResult(
                action="create_new",
                reason="No matching files found",
                confidence=1.0
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Error during move detection analysis",
                operation="analyze_file",
                object_key=stored_obj.object_key,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms
            )
            # Default to creating new on error
            return MoveDetectionResult(
                action="create_new",
                reason=f"Error during analysis: {str(e)}",
                confidence=0.0
            )
    
    async def _verify_with_content_hash(
        self, 
        stored_obj: StoredMediaObject, 
        candidates: List[MediaObjectRecord]
    ) -> Optional[MediaObjectRecord]:
        """Verify potential matches using content hash."""
        try:
            # Get content from storage provider
            content = await self.storage_provider.retrieve(stored_obj.object_key)
            new_file_hash = compute_content_hash_sync(content)
            
            if not new_file_hash:
                logger.warning(
                    "Failed to compute content hash for new file",
                    operation="verify_content_hash",
                    object_key=stored_obj.object_key
                )
                return None
            
            # Check candidates for matching hash
            for candidate in candidates:
                if candidate.content_hash == new_file_hash:
                    logger.debug(
                        "Content hash match found",
                        operation="verify_content_hash",
                        object_key=stored_obj.object_key,
                        candidate_key=candidate.object_key,
                        content_hash=new_file_hash
                    )
                    return candidate
                    
            # No hash match - need to compute hashes for candidates without them
            for candidate in candidates:
                if not candidate.content_hash:
                    # Try to get content for candidate and compute hash
                    try:
                        candidate_content = await self.storage_provider.retrieve(candidate.object_key)
                        candidate_hash = compute_content_hash_sync(candidate_content)
                        
                        if candidate_hash == new_file_hash:
                            logger.info(
                                "Content hash match found (computed candidate hash)",
                                operation="verify_content_hash",
                                object_key=stored_obj.object_key,
                                candidate_key=candidate.object_key,
                                content_hash=new_file_hash
                            )
                            # Update candidate record with computed hash
                            # Note: This would require a repository method to update just the hash
                            return candidate
                            
                    except Exception as e:
                        logger.warning(
                            "Failed to compute hash for candidate",
                            operation="verify_content_hash",
                            candidate_key=candidate.object_key,
                            error=str(e)
                        )
                        continue
            
            return None
            
        except Exception as e:
            logger.error(
                "Error during content hash verification",
                operation="verify_content_hash",
                object_key=stored_obj.object_key,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def _verify_move_vs_copy(
        self, 
        existing_record: MediaObjectRecord,
        stored_obj: StoredMediaObject
    ) -> bool:
        """Verify if this is a move (source gone) vs copy (source still exists).
        
        Args:
            existing_record: The potentially moved record
            stored_obj: The newly discovered file
            
        Returns:
            True if it's a move (source file no longer exists), False if it's a copy
        """
        try:
            # Check if original file still exists at old location
            old_items = self.storage_provider.list_directory(
                prefix=existing_record.object_key.rsplit('/', 1)[0] if '/' in existing_record.object_key else None
            )
            
            # Look for the original file in the directory listing
            old_filename = existing_record.object_key.split('/')[-1]
            for item in old_items:
                if not item.is_folder and item.name == old_filename:
                    logger.debug(
                        "Original file still exists - this is a copy",
                        operation="verify_move_vs_copy",
                        original_key=existing_record.object_key,
                        new_key=stored_obj.object_key
                    )
                    return False  # Copy
            
            logger.debug(
                "Original file no longer exists - this is a move",
                operation="verify_move_vs_copy",
                original_key=existing_record.object_key,
                new_key=stored_obj.object_key
            )
            return True  # Move
            
        except Exception as e:
            logger.warning(
                "Error checking if original file exists - assuming move",
                operation="verify_move_vs_copy",
                original_key=existing_record.object_key,
                new_key=stored_obj.object_key,
                error=str(e)
            )
            # Default to move on error
            return True