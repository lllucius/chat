"""Helper utility functions."""

import re
import uuid
from typing import List, Optional
from pathlib import Path


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted file size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = "unnamed_file"
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        max_name_length = 255 - len(ext)
        sanitized = name[:max_name_length] + ext
    
    return sanitized


def generate_unique_filename(original_filename: str, existing_files: List[str]) -> str:
    """
    Generate a unique filename to avoid conflicts.
    
    Args:
        original_filename: Original filename
        existing_files: List of existing filenames
        
    Returns:
        Unique filename
    """
    if original_filename not in existing_files:
        return original_filename
    
    name = Path(original_filename).stem
    ext = Path(original_filename).suffix
    
    counter = 1
    while True:
        new_filename = f"{name}_{counter}{ext}"
        if new_filename not in existing_files:
            return new_filename
        counter += 1


def parse_tags(tags_string: Optional[str]) -> List[str]:
    """
    Parse comma-separated tags string into list.
    
    Args:
        tags_string: Comma-separated tags string
        
    Returns:
        List of cleaned tags
    """
    if not tags_string:
        return []
    
    # Split by comma and clean up
    tags = [tag.strip().lower() for tag in tags_string.split(",")]
    
    # Remove empty tags and duplicates
    tags = list(set(tag for tag in tags if tag))
    
    # Sort for consistency
    tags.sort()
    
    return tags


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to specified length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    if max_length <= len(suffix):
        return suffix[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


def extract_mentions(text: str) -> List[str]:
    """
    Extract @mentions from text.
    
    Args:
        text: Text to extract mentions from
        
    Returns:
        List of mentioned usernames
    """
    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, text)
    return list(set(mentions))  # Remove duplicates


def extract_hashtags(text: str) -> List[str]:
    """
    Extract #hashtags from text.
    
    Args:
        text: Text to extract hashtags from
        
    Returns:
        List of hashtags
    """
    hashtag_pattern = r'#(\w+)'
    hashtags = re.findall(hashtag_pattern, text)
    return list(set(hashtags))  # Remove duplicates


def generate_short_id(length: int = 8) -> str:
    """
    Generate a short unique ID.
    
    Args:
        length: Length of the ID
        
    Returns:
        Short unique ID
    """
    return str(uuid.uuid4()).replace('-', '')[:length]


def clean_whitespace(text: str) -> str:
    """
    Clean excessive whitespace from text.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Replace multiple newlines with double newline
    text = re.sub(r'\n+', '\n\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def mask_sensitive_data(text: str) -> str:
    """
    Mask sensitive data in text for logging.
    
    Args:
        text: Text that may contain sensitive data
        
    Returns:
        Text with sensitive data masked
    """
    # Mask email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***', text)
    
    # Mask phone numbers (simple pattern)
    text = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '***-***-****', text)
    text = re.sub(r'\b\(\d{3}\)\s?\d{3}-\d{4}\b', '(***) ***-****', text)
    
    # Mask credit card numbers (simple pattern)
    text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '****-****-****-****', text)
    
    # Mask SSN (simple pattern)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '***-**-****', text)
    
    return text


def calculate_similarity_score(text1: str, text2: str) -> float:
    """
    Calculate simple similarity score between two texts.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    # Convert to lowercase and split into words
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings near the chunk boundary
            sentence_end = max(
                text.rfind('.', start, end),
                text.rfind('!', start, end),
                text.rfind('?', start, end)
            )
            
            if sentence_end > start + chunk_size * 0.7:  # Good break point found
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks