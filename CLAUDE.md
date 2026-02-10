# Dani Portfolio - Video Editor Portfolio Website

## Project Overview
A portfolio website for Daniel Aparecido (Video Editor and Motion Designer) showcasing video work from YouTube, Instagram, and TikTok.

## Tech Stack
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Backend**: Static site (no server)
- **Data Source**: Google Sheets (synced via Python script)
- **Hosting**: Vercel (auto-deploys from GitHub)
- **CI/CD**: GitHub Actions (daily stats refresh at 9:00 AM UTC)

## Project Structure
```
Dani Portifolio/
├── index.html              # Main portfolio page
├── about.html              # About page
├── js/
│   ├── projects.js         # AUTO-GENERATED - video data from Google Sheets
│   └── main.js             # Grid, lightbox, hover previews
├── css/
│   └── styles.css          # All styling, responsive grid
├── scripts/
│   ├── sync_from_sheet.py  # Google Sheets sync + projects.js generation
│   ├── process-videos.ps1  # Video download + preview creation
│   ├── update-portfolio.bat # One-click full update
│   ├── sync-videos.bat     # Only sync from sheet
│   └── process-videos.bat  # Only process videos
├── videos/
│   ├── source/             # Full downloaded videos (gitignored)
│   └── previews/           # 30-sec preview clips
├── images/
│   └── thumbnails/         # Local thumbnails (Instagram/TikTok)
├── .github/workflows/
│   └── update-videos.yml   # Daily stats refresh workflow
└── .claude/
    └── skills/             # Claude Code skills
```

## Workflow

### Adding New Videos
1. Add video URL to Google Sheet (appropriate tab: Long-term, Short-term, or Motion Design)
2. Run `scripts/update-portfolio.bat`
   - Syncs metadata from Google Sheet
   - Downloads video and thumbnail (Instagram/TikTok)
   - Creates 30-second preview clip
   - Updates `js/projects.js`
3. Commit and push to GitHub
4. Vercel auto-deploys

### Platform Behavior
| Platform  | Thumbnail Source | Hover Preview | Click Action | Lightbox Content |
|-----------|------------------|---------------|--------------|------------------|
| YouTube   | YouTube CDN      | Local .mp4    | Lightbox | YouTube embed + "Watch on YouTube" button |
| Instagram | Local file       | Local .mp4    | Lightbox | Local full video + "Watch on Instagram" button |
| TikTok    | Local file       | Local .mp4    | Lightbox | Local full video + "Watch on TikTok" button |

**All platforms now open in lightbox** with:
- Full video playback (YouTube: embed, Instagram/TikTok: local source video)
- "Watch on [Platform]" button (top-right, opens original URL in new tab)
- Clean HTML5 controls for local videos
- Glassmorphism pill button design

### Automated Stats Refresh
GitHub Actions runs daily at 9:00 AM UTC:
1. Fetches latest view counts from YouTube API / yt-dlp
2. Updates Google Sheet
3. Regenerates `projects.js`
4. Commits changes
5. Triggers Vercel deploy hook

## Environment Variables (.env)
```
YOUTUBE_API_KEY=your_youtube_api_key
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_SERVICE_ACCOUNT_FILE=path/to/credentials.json
```

## Google Sheet Structure
| Tab | Category | Columns |
|-----|----------|---------|
| Long-term | long-form | URL, Video ID, Title, Channel, Views, Last Updated |
| Short-term | short-form | URL, Video ID, Title, Channel, Views, Likes, Last Updated |
| Motion Design | motion-design | URL, Video ID, Title, Channel, Views, Last Updated |

## Claude Code Skills
- `/sync-videos` - Sync from Google Sheet and update projects.js
- `/update-docs` - Update all CLAUDE.md files to reflect current codebase (global)

## Subtree Memory Files
Each directory has its own CLAUDE.md with specific context:
- `scripts/CLAUDE.md` - Script parameters and workflow
- `js/CLAUDE.md` - JavaScript functions and behavior
- `css/CLAUDE.md` - Design system and components
- `.github/CLAUDE.md` - GitHub Actions configuration
- `.claude/CLAUDE.md` - Skills and agents

Run `/update-docs` to refresh all memory files after significant changes.
