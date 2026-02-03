# GitHub Configuration

## Workflows

### update-videos.yml
Automated workflow that refreshes video stats daily.

**Triggers:**
- Schedule: Daily at 9:00 AM UTC (`cron: '0 9 * * *'`)
- Manual: `workflow_dispatch`

**Steps:**
1. Checkout repository
2. Setup Python 3.10
3. Install dependencies (gspread, google-auth, python-dotenv, yt-dlp)
4. Run `sync_from_sheet.py --refresh`
5. Commit changes if any
6. Trigger Vercel deploy hook

**Required Secrets:**
| Secret | Purpose |
|--------|---------|
| `YOUTUBE_API_KEY` | YouTube Data API key |
| `GOOGLE_SHEET_ID` | Portfolio spreadsheet ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service account credentials (JSON string) |
| `VERCEL_DEPLOY_HOOK` | Vercel deploy hook URL |

**Permissions:**
```yaml
permissions:
  contents: write  # Required for git push
```

## Notes
- Workflow only commits if there are actual changes
- Uses `Co-Authored-By: github-actions[bot]` for commits
- Vercel deploy hook ensures site updates even without code changes
- Stats refresh uses `--refresh` flag (only updates views/likes, not full metadata)
