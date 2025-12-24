from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Comment:
    cid: str
    text: str
    time: str
    author: str
    channel: str
    votes: str
    replies: str
    photo: str
    heart: bool
    reply: bool
