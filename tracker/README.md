# YouTube Video Tracker

Paste YouTube video URLs into a Google Sheet, and this script automatically fetches video data (title, channel, views, likes, etc.). Runs via GitHub Actions daily or manually.

## How It Works

1. You paste YouTube video URLs in column A of the "Videos" sheet
2. The script reads all URLs, fetches data from YouTube API
3. Columns B-J are populated with video metadata

## Sheet Structure

| URL | Video ID | Title | Channel | Views | Likes | Comments | Published | Thumbnail | Last Updated |
|-----|----------|-------|---------|-------|-------|----------|-----------|-----------|--------------|
| (you paste) | (auto) | (auto) | (auto) | (auto) | (auto) | (auto) | (auto) | (auto) | (auto) |

## Setup

### 1. Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable these APIs:
   - YouTube Data API v3
   - Google Sheets API
   - Google Drive API

### 2. Get YouTube API Key

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > API Key**
3. Copy the key

### 3. Create Service Account

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > Service Account**
3. Name it, click through to finish
4. Click on the service account > **Keys** > **Add Key** > **Create new key** > **JSON**
5. Download the JSON file

### 4. Set Up Google Sheet

1. Create a new Google Sheet
2. Copy the Sheet ID from URL: `https://docs.google.com/spreadsheets/d/SHEET_ID/edit`
3. Share the sheet with the service account email (from the JSON file's `client_email`)
4. Give it **Editor** access

The "Videos" sheet with headers will be created automatically on first run.

### 5. Local Setup

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your values
```

Run:
```bash
python main.py
```

### 6. GitHub Actions

Add these repository secrets (**Settings > Secrets > Actions**):

| Secret | Value |
|--------|-------|
| `YOUTUBE_API_KEY` | Your YouTube API key |
| `GOOGLE_SHEET_ID` | Your Google Sheet ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Entire contents of service account JSON file |

The workflow runs daily at 9:00 AM UTC. Manual trigger available in Actions tab.

## Usage

1. Open your Google Sheet
2. Paste YouTube video URLs in column A (one per row)
3. Run the script (or wait for scheduled run)
4. Data appears in columns B-J

Supported URL formats:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`
