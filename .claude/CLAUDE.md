# Claude Code Configuration

## Skills

### /sync-videos (Project-specific)
Sync video data from Google Sheets and update projects.js.

**Location:** `skills/sync-videos/SKILL.md`

**Usage:**
- `/sync-videos` - Populate new videos and regenerate projects.js
- `/sync-videos --refresh` - Only update stats for existing videos
- `/sync-videos --download` - Also download and process preview videos

### /update-docs (Global)
Update all CLAUDE.md memory files to reflect current codebase state.

**Location:** `~/.claude/skills/update-docs/SKILL.md` (global)

**Usage:**
- `/update-docs` - Scan project and update all CLAUDE.md files

**Updates these files:**
- `CLAUDE.md` (root)
- `scripts/CLAUDE.md`
- `js/CLAUDE.md`
- `css/CLAUDE.md`
- `.github/CLAUDE.md`
- `.claude/CLAUDE.md`

## Agents

### frontend-designer
Agent for ensuring UI components follow the design system.

**Location:** `agents/frontend-designer.md`

## Settings

### settings.json
Shared project settings (committed to git).

### settings.local.json
Local overrides (gitignored).
- Contains user-specific paths
- API keys should be in .env, not here
