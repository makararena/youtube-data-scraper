from __future__ import annotations


def sanitize_name(name: str) -> str:
    """Convert channel/video identifiers into safe folder names."""
    return name.replace("@", "").replace("/", "_").replace("\\", "_")
