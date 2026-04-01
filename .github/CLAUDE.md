# GitHub Configuration

## Workflows

### deploy.yml
Deploys the site to GitHub Pages on every push to main.

**Triggers:**
- Push to `main` branch
- Manual: `workflow_dispatch`

**Steps:**
1. Checkout repository
2. Configure GitHub Pages
3. Upload artifact (entire repo root)
4. Deploy to GitHub Pages

**Permissions:**
```yaml
permissions:
  contents: read
  pages: write
  id-token: write
```

**Concurrency:** Only one deployment at a time (group: `pages`, cancels in-progress)

### update-videos.yml
Automated workflow that refreshes video stats daily.

**Triggers:**
- Schedule: Daily at 9:00 AM UTC (`cron: '0 9 * * *'`)
- Manual: `workflow_dispatch`

**Steps:**
1. Checkout repository
2. Setup Python 3.11
3. Install dependencies from requirements.txt
4. Run `sync_from_sheet.py --refresh`
5. Commit and push changes if any (triggers GitHub Pages deploy automatically)

**Required Secrets:**
| Secret | Purpose |
|--------|---------|
| `YOUTUBE_API_KEY` | YouTube Data API key |
| `GOOGLE_SHEET_ID` | Portfolio spreadsheet ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service account credentials (JSON string) |

**Permissions:**
```yaml
permissions:
  contents: write  # Required for git push
```

## Notes
- Workflow only commits if there are actual changes to `js/projects.js`
- Uses `github-actions[bot]` for automated commits
- Pushing to main triggers `deploy.yml` automatically, so no separate deploy hook needed
- Stats refresh uses `--refresh` flag (only updates views/likes, not full metadata)
