"""Path normalization utilities for consistent object key handling."""


def normalize_object_key(object_key: str) -> str:
    """
    Normalize an object key to remove leading slashes.
    
    This ensures all object keys in our application are stored and processed
    consistently without leading slashes, regardless of what storage providers return.
    
    Args:
        object_key: The raw object key from storage provider
        
    Returns:
        Normalized object key without leading slash
        
    Examples:
        >>> normalize_object_key("/photos/image.jpg")
        "photos/image.jpg"
        >>> normalize_object_key("photos/image.jpg") 
        "photos/image.jpg"
        >>> normalize_object_key("")
        ""
    """
    if not object_key:
        return object_key
    return object_key.lstrip("/")


def normalize_prefix(prefix: str) -> str:
    """
    Normalize a path prefix to remove leading slashes.
    
    Args:
        prefix: The raw prefix
        
    Returns:
        Normalized prefix without leading slash
    """
    if not prefix:
        return prefix
    return prefix.lstrip("/")