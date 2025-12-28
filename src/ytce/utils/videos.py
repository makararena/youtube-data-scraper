from __future__ import annotations

import re
from typing import List


def parse_videos_file(file_path: str) -> List[str]:
    """
    Parse a videos file and extract valid video IDs.
    
    Supports:
    - Video ID (11 characters, e.g., dQw4w9WgXcQ)
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID&t=123s (extracts just the ID)
    
    Ignores:
    - Empty lines
    - Lines starting with #
    - Whitespace
    
    Args:
        file_path: Path to videos file
    
    Returns:
        List of video IDs
    
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    videos = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Strip whitespace
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Extract video ID
            video_id = extract_video_id(line)
            
            if video_id:
                videos.append(video_id)
            else:
                # Log warning but continue (don't fail)
                print(f"⚠️  Line {line_num}: Skipping invalid video ID: {line}")
    
    return videos


def extract_video_id(text: str) -> str | None:
    """
    Extract video ID from various formats.
    
    Returns:
        Video ID (11 characters) or None if invalid
    """
    text = text.strip()
    
    # Direct video ID (11 characters, alphanumeric, hyphens, underscores)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', text):
        return text
    
    # Full URL: https://www.youtube.com/watch?v=VIDEO_ID
    match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', text)
    if match:
        return match.group(1)
    
    # Short URL: https://youtu.be/VIDEO_ID
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', text)
    if match:
        return match.group(1)
    
    # Embed URL: https://www.youtube.com/embed/VIDEO_ID
    match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})', text)
    if match:
        return match.group(1)
    
    return None

