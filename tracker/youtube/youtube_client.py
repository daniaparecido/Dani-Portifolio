"""YouTube Data API client for fetching video data."""

import re
import time
import logging
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def parse_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration (PT1H2M3S) to HH:MM:SS format."""
    if not iso_duration:
        return ""

    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return iso_duration

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class YouTubeClient:
    """Client for interacting with YouTube Data API v3."""

    def __init__(self, api_key: str):
        self.youtube = build("youtube", "v3", developerKey=api_key)
        self.request_count = 0

    def _handle_rate_limit(self, func, *args, **kwargs):
        """Execute API call with rate limit handling."""
        max_retries = 3
        base_delay = 5

        for attempt in range(max_retries):
            try:
                self.request_count += 1
                return func(*args, **kwargs).execute()
            except HttpError as e:
                if e.resp.status == 403 and "quotaExceeded" in str(e):
                    logger.error("YouTube API quota exceeded. Try again tomorrow.")
                    raise
                elif e.resp.status == 429:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limited. Waiting {delay}s before retry...")
                    time.sleep(delay)
                else:
                    raise
        raise Exception("Max retries exceeded for API call")

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
            r"(?:embed/)([a-zA-Z0-9_-]{11})",
            r"(?:shorts/)([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_details(self, video_ids: list[str]) -> dict[str, dict]:
        """Fetch detailed information for multiple videos. Returns dict keyed by video ID."""
        results = {}

        # YouTube API allows max 50 video IDs per request
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            logger.info(f"Fetching details for videos {i + 1}-{i + len(batch)}...")

            request = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(batch)
            )
            response = self._handle_rate_limit(lambda: request)

            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                content_details = item.get("contentDetails", {})

                results[item["id"]] = {
                    "video_id": item["id"],
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "duration": parse_duration(content_details.get("duration", "")),
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "published": snippet.get("publishedAt", "")[:10],
                    "thumbnail": self._get_best_thumbnail(snippet.get("thumbnails", {})),
                }

        return results

    def get_video_stats(self, video_ids: list[str]) -> dict[str, dict]:
        """Fetch only statistics for multiple videos. Returns dict keyed by video ID."""
        results = {}

        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            logger.info(f"Fetching stats for videos {i + 1}-{i + len(batch)}...")

            request = self.youtube.videos().list(
                part="statistics",
                id=",".join(batch)
            )
            response = self._handle_rate_limit(lambda: request)

            for item in response.get("items", []):
                stats = item.get("statistics", {})
                results[item["id"]] = {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                }

        return results

    def _get_best_thumbnail(self, thumbnails: dict) -> str:
        """Get the highest quality thumbnail URL available."""
        for quality in ["maxres", "standard", "high", "medium", "default"]:
            if quality in thumbnails:
                return thumbnails[quality].get("url", "")
        return ""
