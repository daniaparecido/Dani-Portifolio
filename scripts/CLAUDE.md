# Scripts Directory

## Files

### sync_from_sheet.py
Main sync script that connects Google Sheets to the website.

**Modes:**
- `--populate` - Fetch metadata for new URLs (default)
- `--refresh` - Update stats for existing videos
- `--generate` - Only regenerate projects.js (no API calls)
- `--download` - Also download/process preview videos
- `--fetch-thumbnails` - Fetch thumbnails for Instagram/TikTok
- `--dry-run` - Show what would be done without making changes

**Worksheet Config:**
```python
WORKSHEET_CONFIG = {
    "Long-term": {"category": "long-form", "type": "youtube"},
    "Short-term": {"category": "short-form", "type": "mixed"},
    "Motion Design": {"category": "motion-design", "type": "youtube"},
}
```

**Clients:**
- `YouTubeClient` - YouTube Data API v3 for metadata/stats
- `SocialMediaClient` - yt-dlp wrapper for Instagram/TikTok
- `SheetsClient` - gspread wrapper for Google Sheets

### process-videos.ps1
PowerShell script for downloading videos and creating previews.

**Parameters:**
- `-Url "URL"` - Download from any URL (Instagram/TikTok/YouTube)
- `-Download ID` - Download specific YouTube video
- `-Process ID` - Create preview for existing video
- `-All ID` - Download + process + get metadata
- `-Metadata ID` - Just fetch metadata (no download)
- `-NoPause` - Skip "Press Enter to exit" (for automation)

**Output Directories:**
- Source videos: `videos/source/{id}.mp4`
- Previews: `videos/previews/{id}.mp4` (30 sec, no audio)
- Thumbnails: `images/thumbnails/{id}.jpg` (Instagram/TikTok only)

**Preview Specs:**
- YouTube: 854x480 (horizontal)
- Instagram/TikTok: 540x960 (vertical)
- Codec: H.264, CRF 28, no audio

### Batch Files

| File | Purpose |
|------|---------|
| `update-portfolio.bat` | Full sync + download (recommended one-click solution) |
| `sync-videos.bat` | Only sync from Google Sheet |
| `process-videos.bat` | Only process videos manually |
