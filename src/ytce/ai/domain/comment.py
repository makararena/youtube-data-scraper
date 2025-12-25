from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Comment:
    """
    Domain representation of a single comment.
    Immutable. No logic.
    """

    id: str
    text: str

    # optional metadata (not used by AI directly, but useful later)
    author: Optional[str] = None
    channel: Optional[str] = None
    votes: Optional[int] = None
    raw: Optional[Dict[str, Any]] = None


__all__ = ["Comment"]
