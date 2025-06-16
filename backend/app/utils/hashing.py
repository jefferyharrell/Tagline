"""Utilities for content hashing used in move detection."""

import hashlib
import time
from typing import AsyncIterator, Optional

from app.structlog_config import get_logger

logger = get_logger(__name__)


async def compute_content_hash(content_iter: AsyncIterator[bytes]) -> Optional[str]:
    """Compute SHA-256 hash of content from an async iterator.
    
    Args:
        content_iter: Async iterator yielding bytes chunks
        
    Returns:
        Hex string of SHA-256 hash, or None if error occurred
    """
    hasher = hashlib.sha256()
    total_bytes = 0
    start_time = time.time()
    
    try:
        logger.debug(
            "Starting content hash computation",
            operation="compute_hash",
            algorithm="sha256"
        )
        
        async for chunk in content_iter:
            hasher.update(chunk)
            total_bytes += len(chunk)
            
        content_hash = hasher.hexdigest()
        duration_ms = (time.time() - start_time) * 1000
        
        logger.debug(
            "Content hash computed successfully",
            operation="compute_hash",
            algorithm="sha256",
            hash=content_hash,
            total_bytes=total_bytes,
            duration_ms=duration_ms
        )
        
        return content_hash
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Failed to compute content hash",
            operation="compute_hash",
            algorithm="sha256",
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=duration_ms
        )
        return None


def compute_content_hash_sync(content: bytes) -> Optional[str]:
    """Compute SHA-256 hash of content bytes (synchronous version).
    
    Args:
        content: Bytes to hash
        
    Returns:
        Hex string of SHA-256 hash, or None if error occurred
    """
    try:
        start_time = time.time()
        
        logger.debug(
            "Starting synchronous content hash computation",
            operation="compute_hash_sync",
            algorithm="sha256",
            content_size=len(content)
        )
        
        hasher = hashlib.sha256()
        hasher.update(content)
        content_hash = hasher.hexdigest()
        
        duration_ms = (time.time() - start_time) * 1000
        
        logger.debug(
            "Synchronous content hash computed successfully",
            operation="compute_hash_sync",
            algorithm="sha256",
            hash=content_hash,
            content_size=len(content),
            duration_ms=duration_ms
        )
        
        return content_hash
        
    except Exception as e:
        logger.error(
            "Failed to compute synchronous content hash",
            operation="compute_hash_sync",
            algorithm="sha256",
            error=str(e),
            error_type=type(e).__name__,
            content_size=len(content) if content else 0
        )
        return None


async def compute_quick_hash(content_iter: AsyncIterator[bytes], max_bytes: int = 4096) -> Optional[str]:
    """Compute SHA-256 hash of first N bytes for quick fingerprinting.
    
    Args:
        content_iter: Async iterator yielding bytes chunks
        max_bytes: Maximum number of bytes to hash (default 4KB)
        
    Returns:
        Hex string of SHA-256 hash of first max_bytes, or None if error occurred
    """
    hasher = hashlib.sha256()
    total_bytes = 0
    start_time = time.time()
    
    try:
        logger.debug(
            "Starting quick hash computation",
            operation="compute_quick_hash",
            algorithm="sha256",
            max_bytes=max_bytes
        )
        
        async for chunk in content_iter:
            remaining = max_bytes - total_bytes
            if remaining <= 0:
                break
                
            chunk_to_hash = chunk[:remaining] if len(chunk) > remaining else chunk
            hasher.update(chunk_to_hash)
            total_bytes += len(chunk_to_hash)
            
        quick_hash = hasher.hexdigest()
        duration_ms = (time.time() - start_time) * 1000
        
        logger.debug(
            "Quick hash computed successfully",
            operation="compute_quick_hash",
            algorithm="sha256",
            hash=quick_hash,
            bytes_hashed=total_bytes,
            max_bytes=max_bytes,
            duration_ms=duration_ms
        )
        
        return quick_hash
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Failed to compute quick hash",
            operation="compute_quick_hash",
            algorithm="sha256",
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=duration_ms
        )
        return None