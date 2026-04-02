"""Debug script to see all fields returned by yt-dlp for Instagram."""
import yt_dlp
import json

# Test with one URL - replace with an actual Instagram URL from your sheet
TEST_URL = "https://www.instagram.com/p/DSOCy0qk1F3/"

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'cookiefile': 'cookies.txt',
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(TEST_URL, download=False)

    # Print all keys and their values
    print("=" * 60)
    print("ALL FIELDS RETURNED BY YT-DLP:")
    print("=" * 60)
    for key, value in sorted(info.items()):
        if not key.startswith('_') and key not in ['formats', 'thumbnails', 'subtitles', 'requested_formats']:
            print(f"{key}: {value}")

    print("\n" + "=" * 60)
    print("SPECIFIC VIEW-RELATED FIELDS:")
    print("=" * 60)
    for key in info.keys():
        if 'view' in key.lower() or 'play' in key.lower() or 'count' in key.lower():
            print(f"{key}: {info[key]}")
