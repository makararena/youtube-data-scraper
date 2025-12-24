from __future__ import annotations

from typing import Optional

from ytce.storage.writers import write_json
from ytce.youtube.channel_videos import YoutubeChannelVideosScraper


def run(*, channel_id: str, output: str, max_videos: Optional[int], debug: bool) -> None:
    scraper = YoutubeChannelVideosScraper(debug=debug)
    videos = scraper.get_all_videos(channel_id, max_videos=max_videos, show_progress=True)
    write_json(output, {"channel_id": channel_id, "total_videos": len(videos), "videos": videos})
    print(f"\nOK: Wrote videos JSON: {output}")
