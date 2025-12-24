from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    url: str
    order: int
    channel_id: str = ""
    view_count: Optional[int] = None
    view_count_raw: str = ""
    length: str = ""
    thumbnail_url: str = ""
