from __future__ import annotations

import os
from typing import Optional

from ytce.storage.paths import channel_comments_dir, video_comments_filename
from ytce.storage.resume import should_skip_existing
from ytce.storage.writers import ensure_dir, write_json, write_jsonl
from ytce.youtube.channel_videos import YoutubeChannelVideosScraper
from ytce.youtube.comments import SORT_BY_POPULAR, SORT_BY_RECENT, YoutubeCommentDownloader


def run(
    *,
    channel_id: str,
    out_dir: str,
    max_videos: Optional[int],
    sort: str,
    per_video_limit: Optional[int],
    language: Optional[str],
    resume: bool,
    debug: bool,
) -> None:
    ensure_dir(out_dir)
    comments_dir = channel_comments_dir(out_dir)
    ensure_dir(comments_dir)

    # 1) Videos metadata
    vs = YoutubeChannelVideosScraper(debug=debug)
    videos = vs.get_all_videos(channel_id, max_videos=max_videos, show_progress=True)
    videos_path = os.path.join(out_dir, "videos.json")
    write_json(videos_path, {"channel_id": channel_id, "total_videos": len(videos), "videos": videos})
    print(f"\nOK: Wrote channel videos: {videos_path}")

    # 2) Comments per video
    cd = YoutubeCommentDownloader()
    sort_by = SORT_BY_RECENT if sort == "recent" else SORT_BY_POPULAR

    for v in videos:
        video_id = v["video_id"]
        order = v.get("order", 0)
        safe_name = video_comments_filename(order, video_id)
        out_path = os.path.join(comments_dir, safe_name)

        if should_skip_existing(out_path, resume=resume):
            print(f"Skipping existing comments: {safe_name}")
            continue

        print(f"\n=== [{order}/{len(videos)}] Comments for {video_id} ===")
        gen = cd.get_comments(video_id, sort_by=sort_by, language=language, sleep=0.1)

        def limited():
            count = 0
            for c in gen:
                yield c
                count += 1
                if per_video_limit is not None and count >= per_video_limit:
                    break

        wrote = write_jsonl(out_path, limited())
        print(f"OK: Wrote {wrote} comments -> {out_path}")
