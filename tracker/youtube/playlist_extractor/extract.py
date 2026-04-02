"""Extract all video URLs from a YouTube playlist."""

import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from googleapiclient.discovery import build


def extract_playlist_id(url: str) -> str | None:
    """Extract playlist ID from YouTube URL."""
    patterns = [
        r"[?&]list=([a-zA-Z0-9_-]+)",
        r"playlist\?list=([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_playlist_videos(api_key: str, playlist_id: str) -> list[str]:
    """Fetch all video URLs from a playlist."""
    youtube = build("youtube", "v3", developerKey=api_key)
    video_urls = []
    next_page_token = None

    print(f"Fetching videos from playlist: {playlist_id}")

    while True:
        request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response.get("items", []):
            video_id = item["contentDetails"]["videoId"]
            video_urls.append(f"https://www.youtube.com/watch?v={video_id}")

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

        print(f"  Fetched {len(video_urls)} videos so far...")

    return video_urls


def main():
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: YOUTUBE_API_KEY not found in .env")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python extract.py <playlist_url>")
        print("Example: python extract.py https://www.youtube.com/playlist?list=PLxxxxx")
        sys.exit(1)

    playlist_url = sys.argv[1]
    playlist_id = extract_playlist_id(playlist_url)

    if not playlist_id:
        print(f"Error: Could not extract playlist ID from URL: {playlist_url}")
        sys.exit(1)

    video_urls = get_playlist_videos(api_key, playlist_id)

    print(f"\n{'='*50}")
    print(f"Found {len(video_urls)} videos")
    print("="*50)
    print("\nVideo URLs (copy these to your Google Sheet):\n")

    for url in video_urls:
        print(url)


if __name__ == "__main__":
    main()
