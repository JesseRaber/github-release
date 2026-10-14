# Install - GitHub Release (Claude Code plugin)

For the Claude app uploader use `-UNIVERSAL-skill.zip` instead; it rejects plugin files.

Extract the outer `github-release/` folder to a permanent location, then in Claude Code:

```text
/plugin marketplace add <path-to>/github-release
/plugin install github-release
```

Or add the GitHub repository as a marketplace once it exists.

When replacing an older copy, keep the backup outside every folder the app scans for skills (or rename its `SKILL.md` to `SKILL.backup-not-loaded.md`), then restart the app before checking which version it loaded.
