#!/usr/bin/env python3
"""
Unified CLI for this repo:
- Download channel videos metadata (newest -> oldest)
- Download comments for a single video
- Download all channel videos + recursively download comments per video

Outputs are designed for easy processing:
- videos metadata: JSON
- comments: JSONL (one comment per line)
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from typing import Any, Dict, Iterable, Optional


REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
YOUTUBE_CHANNEL_VIDEOS_DIR = os.path.join(REPO_ROOT, "youtube-channel-videos")
YOUTUBE_COMMENT_DOWNLOADER_DIR = os.path.join(REPO_ROOT, "youtube-comment-downloader")

for p in (REPO_ROOT, YOUTUBE_CHANNEL_VIDEOS_DIR, YOUTUBE_COMMENT_DOWNLOADER_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from channel_videos import YoutubeChannelVideosScraper  # type: ignore  # noqa: E402
from downloader import (  # type: ignore  # noqa: E402
    SORT_BY_POPULAR,
    SORT_BY_RECENT,
    YoutubeCommentDownloader,
)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _write_json(path: str, payload: Any) -> None:
    _ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _write_jsonl(path: str, items: Iterable[Dict[str, Any]]) -> int:
    _ensure_dir(os.path.dirname(path) or ".")
    count = 0
    with io.open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
    return count


def export_channel_videos(*, channel_id: str, output: str, max_videos: Optional[int], debug: bool) -> None:
    scraper = YoutubeChannelVideosScraper(debug=debug)
    videos = scraper.get_all_videos(channel_id, max_videos=max_videos, show_progress=True)
    _write_json(output, {"channel_id": channel_id, "total_videos": len(videos), "videos": videos})
    print(f"\n✅ Wrote videos JSON: {output}")


def export_video_comments(
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

    wrote = _write_jsonl(output, limited())
    print(f"\n✅ Wrote comments JSONL: {output} ({wrote} comments)")


def export_channel_comments(
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
    _ensure_dir(out_dir)
    comments_dir = os.path.join(out_dir, "comments")
    _ensure_dir(comments_dir)

    # 1) Videos metadata
    vs = YoutubeChannelVideosScraper(debug=debug)
    videos = vs.get_all_videos(channel_id, max_videos=max_videos, show_progress=True)
    videos_path = os.path.join(out_dir, "videos.json")
    _write_json(videos_path, {"channel_id": channel_id, "total_videos": len(videos), "videos": videos})
    print(f"\n✅ Wrote channel videos: {videos_path}")

    # 2) Comments per video
    cd = YoutubeCommentDownloader()
    sort_by = SORT_BY_RECENT if sort == "recent" else SORT_BY_POPULAR

    for v in videos:
        video_id = v["video_id"]
        order = v.get("order", 0)
        safe_name = f"{order:04d}_{video_id}.jsonl"
        out_path = os.path.join(comments_dir, safe_name)

        if resume and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
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

        wrote = _write_jsonl(out_path, limited())
        print(f"✅ Wrote {wrote} comments -> {out_path}")


def _sanitize_name(name: str) -> str:
    """Convert channel/video ID to safe folder name."""
    return name.replace("@", "").replace("/", "_").replace("\\", "_")


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="scrape.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_videos = sub.add_parser("videos", help="Download channel videos metadata as JSON (newest -> oldest).")
    p_videos.add_argument("channel_id")
    p_videos.add_argument("-o", "--output", default=None, help="Output path (default: data/<channel>/videos.json)")
    p_videos.add_argument("--max-videos", type=int, default=None)
    p_videos.add_argument("--debug", action="store_true")

    p_comments = sub.add_parser("comments", help="Download comments for a single video as JSONL.")
    p_comments.add_argument("video_id")
    p_comments.add_argument("-o", "--output", default=None, help="Output path (default: data/<video_id>/comments.jsonl)")
    p_comments.add_argument("--sort", choices=["recent", "popular"], default="recent")
    p_comments.add_argument("--limit", type=int, default=None)
    p_comments.add_argument("--language", default=None)

    p_channel = sub.add_parser(
        "channel-comments",
        help="Download channel videos + recursively download comments for each video (per-video JSONL).",
    )
    p_channel.add_argument("channel_id")
    p_channel.add_argument("--out-dir", default=None, help="Output directory (default: data/<channel>)")
    p_channel.add_argument("--max-videos", type=int, default=None)
    p_channel.add_argument("--sort", choices=["recent", "popular"], default="recent")
    p_channel.add_argument("--per-video-limit", type=int, default=None)
    p_channel.add_argument("--language", default=None)
    p_channel.add_argument("--no-resume", action="store_true")
    p_channel.add_argument("--debug", action="store_true")

    args = parser.parse_args(argv)

    # Auto-generate output paths in data/ folder
    if args.cmd == "videos":
        output = args.output or os.path.join("data", _sanitize_name(args.channel_id), "videos.json")
        export_channel_videos(channel_id=args.channel_id, output=output, max_videos=args.max_videos, debug=args.debug)
        return
    if args.cmd == "comments":
        output = args.output or os.path.join("data", _sanitize_name(args.video_id), "comments.jsonl")
        export_video_comments(
            video_id=args.video_id,
            output=output,
            sort=args.sort,
            limit=args.limit,
            language=args.language,
        )
        return
    if args.cmd == "channel-comments":
        out_dir = args.out_dir or os.path.join("data", _sanitize_name(args.channel_id))
        export_channel_comments(
            channel_id=args.channel_id,
            out_dir=out_dir,
            max_videos=args.max_videos,
            sort=args.sort,
            per_video_limit=args.per_video_limit,
            language=args.language,
            resume=not args.no_resume,
            debug=args.debug,
        )
        return


if __name__ == "__main__":
    main()


