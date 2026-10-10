# Install - GitHub Release

| Your AI app | Download |
|---|---|
| **Almost everything**: Claude app skill upload, ChatGPT/Codex standalone skills, Antigravity, local models, any skills folder | `…-UNIVERSAL-skill.zip` |
| Claude Code `/plugin install` (not the Claude app uploader) | `…-claude-code-plugin.zip` |
| Codex / ChatGPT plugin | `…-codex-chatgpt-plugin.zip` |
| Microsoft Copilot agent skill upload, **Grok** | `…-microsoft-copilot-agent-only.zip` |
| Gemini Apps skill upload | `…-gemini-apps-only.zip` |
| Opal skill import | `…-opal-only.zip` |

The folder `github-release/` **is** the skill. Keep `SKILL.md`, `references/`, `scripts/` and `templates/` together.

Host-specific packages leave some files out: Gemini Apps omits the `.yml` workflow templates (precaution) and `templates/gitattributes` (Gemini rejects files without an extension); Opal keeps only `SKILL.md` and `references/*.md`, so the helper scripts and templates are not available there.

## Updating an installed copy

Many apps (Codex observed) load **every** `SKILL.md` anywhere under their skills folder. Never keep the old copy inside that folder: move it beside it (for example `~/.codex/skill-backups/`), or rename its `SKILL.md` to `SKILL.backup-not-loaded.md`. Then check that only one copy carries the name and restart the app:

```bash
python github-release/scripts/check_skill_duplicates.py ~/.codex/skills --name github-release --expect-version 0.2.1
```

## Claude app

Settings -> Capabilities -> Skills -> Upload skill, with the Universal ZIP.

## Local models

Point the system prompt or context loader at `github-release/SKILL.md`.

## Smoke test

> Is my skill repository ready to tag v1.0.0?

A loaded skill states **Mode: Gate** first and reports **Loaded GitHub Release v0.2.1 (SKILL.md at <path>)**.

## Requirements

Python 3.8+, standard library only, for `scripts/check_versions.py`, `scripts/verify_release.py` and `scripts/check_skill_duplicates.py`. All are read-only and need no network.

## Verify what you downloaded

```bash
sha256sum -c SHA256SUMS.txt
```

MIT licensed - see `LICENSE.txt`.
