"""TikTok client for fetching video data using yt-dlp."""

import re
import logging
from typing import Optional
import yt_dlp

logger = logging.getLogger(__name__)


def parse_duration(seconds) -> str:
    """Convert seconds to HH:MM:SS format."""
    if not seconds:
        return "00:00:00"

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class TikTokClient:
    """Client for fetching TikTok video data using yt-dlp."""

    def __init__(self, cookies_from_browser: str = None, cookies_file: str = None):
        self.request_count = 0
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }
        if cookies_file:
            self.ydl_opts['cookiefile'] = cookies_file
        elif cookies_from_browser:
            self.ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL."""
        patterns = [
            r'/video/(\d+)',
            r'/v/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_details(self, urls: list[str]) -> dict[str, dict]:
        """Fetch detailed information for multiple videos. Returns dict keyed by video ID."""
        results = {}

        for url in urls:
            video_id = self.extract_video_id(url)
            if not video_id:
                logger.warning(f"Could not extract video ID from: {url}")
                continue

            try:
                self.request_count += 1
                logger.info(f"Fetching: {url}")

                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                if info:
                    # Clean title: remove newlines, limit length
                    title = info.get("description", info.get("title", "")) or ""
                    title = " ".join(title.split())[:200]  # Collapse whitespace/newlines

                    # TikTok may use play_count
                    views = info.get("view_count") or info.get("play_count") or 0

                    results[video_id] = {
                        "video_id": video_id,
                        "title": title,
                        "channel": info.get("uploader", info.get("creator", "")),
                        "duration": parse_duration(info.get("duration")),
                        "views": int(views),
                        "likes": int(info.get("like_count", 0) or 0),
                        "comments": int(info.get("comment_count", 0) or 0),
                        "published": (info.get("upload_date", "") or "")[:10],
                        "thumbnail": info.get("thumbnail", ""),
                    }
                    # Format published date
                    if results[video_id]["published"] and len(results[video_id]["published"]) == 8:
                        d = results[video_id]["published"]
                        results[video_id]["published"] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"

            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")

        return results

    def get_video_stats(self, urls: list[str]) -> dict[str, dict]:
        """Fetch only statistics for multiple videos. Returns dict keyed by video ID."""
        results = {}

        for url in urls:
            video_id = self.extract_video_id(url)
            if not video_id:
                continue

            try:
                self.request_count += 1
                logger.info(f"Fetching stats: {url}")

                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                if info:
                    views = info.get("view_count") or info.get("play_count") or 0
                    results[video_id] = {
                        "views": int(views),
                        "likes": int(info.get("like_count", 0) or 0),
                        "comments": int(info.get("comment_count", 0) or 0),
                    }

            except Exception as e:
                logger.error(f"Error fetching stats for {url}: {e}")

        return results
