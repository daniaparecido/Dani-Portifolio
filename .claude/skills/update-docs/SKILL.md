# /update-docs

Update all CLAUDE.md memory files across the project to reflect the current state of the codebase.

## Behavior

When invoked, scan the project and update each CLAUDE.md file:

1. **Find all CLAUDE.md files:**
   ```
   CLAUDE.md (root)
   scripts/CLAUDE.md
   js/CLAUDE.md
   css/CLAUDE.md
   .github/CLAUDE.md
   .claude/CLAUDE.md
   ```

2. **For each directory with a CLAUDE.md:**
   - Read all files in that directory
   - Analyze their purpose, exports, key functions
   - Update the CLAUDE.md to accurately document:
     - File purposes and relationships
     - Key functions/classes with brief descriptions
     - Configuration options and parameters
     - Important patterns or conventions

3. **For root CLAUDE.md:**
   - Update project overview if structure changed
   - Update file listings
   - Keep workflow documentation current
   - Reference this skill for future updates

## Guidelines

- Keep documentation concise but complete
- Focus on information useful for AI context
- Include code snippets for complex configurations
- Document relationships between files
- Note any breaking changes or migrations

## Output

After updating, report:
- Which CLAUDE.md files were updated
- Summary of significant changes detected
