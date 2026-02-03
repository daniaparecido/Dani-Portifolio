---
name: sync-videos
description: Sync video projects from Google Sheets. Reads video URLs, fetches YouTube metadata, updates the sheet, and generates projects.js. Use when updating the portfolio from the spreadsheet.
disable-model-invocation: true
allowed-tools: Bash(python *), Read, Edit
---

# Sync Videos from Google Sheets

This skill syncs video data between Google Sheets and the portfolio website.

## What it does

1. **Reads** video URLs from the Google Sheet (Column A)
2. **Fetches** metadata from YouTube API (title, channel, views)
3. **Writes** metadata back to the sheet (columns B-F)
4. **Generates** `js/projects.js` for the website

## Usage

### Populate new videos (default)
Fetches full data for URLs without a Video ID:
```bash
python scripts/sync_from_sheet.py
```

### Refresh stats only
Updates view counts for existing videos (used by GitHub Actions):
```bash
python scripts/sync_from_sheet.py --refresh
```

### Generate only
Regenerates projects.js from sheet data without API calls:
```bash
python scripts/sync_from_sheet.py --generate
```

### With video download
Also downloads and processes preview videos:
```bash
python scripts/sync_from_sheet.py --download
```

## Sheet Structure

Each worksheet (Long-term, Short-term, Motion Design) has:

| Column | Field        | Description                    |
|--------|--------------|--------------------------------|
| A      | URL          | YouTube video URL (you add)    |
| B      | Video ID     | Extracted from URL (auto)      |
| C      | Title        | Video title (auto)             |
| D      | Channel      | Channel name (auto)            |
| E      | Views        | View count (auto-refreshed)    |
| F      | Last Updated | Timestamp (auto)               |

## GitHub Actions

The workflow runs daily at 9:00 AM UTC to:
1. Refresh view counts from YouTube API
2. Update the Google Sheet
3. Regenerate projects.js
4. Commit and push changes

### Required Secrets

Set these in your GitHub repository settings:

- `YOUTUBE_API_KEY` - YouTube Data API v3 key
- `GOOGLE_SHEET_ID` - The spreadsheet ID
- `GOOGLE_SERVICE_ACCOUNT_JSON` - Full service account JSON content

## Local Setup

1. Copy `.env.example` to `.env` and fill in values
2. Place service account JSON in `_key/` folder
3. Run `pip install -r requirements.txt`
4. Share the Google Sheet with the service account email
