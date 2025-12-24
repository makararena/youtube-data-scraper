from __future__ import annotations

from typing import Optional

from ytce.storage.writers import write_jsonl
from ytce.youtube.comments import SORT_BY_POPULAR, SORT_BY_RECENT, YoutubeCommentDownloader


def run(
    *,
    video_id: str,
    output: str,
    sort: str,
    limit: Optional[int],
    language: Optional[str],
) -> None:
    downloader = YoutubeCommentDownloader()
    sort_by = SORT_BY_RECENT if sort == "recent" else SORT_BY_POPULAR

    gen = downloader.get_comments(video_id, sort_by=sort_by, language=language, sleep=0.1)

    def limited():
        nonlocal gen
        count = 0
        for c in gen:
            yield c
            count += 1
            if limit is not None and count >= limit:
                break

    wrote = write_jsonl(output, limited())
    print(f"\nOK: Wrote comments JSONL: {output} ({wrote} comments)")
