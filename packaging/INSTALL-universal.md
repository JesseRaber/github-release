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

Host-specific packages leave some files out: Gemini Apps omits the `.yml` workflow templates (precaution); Opal keeps only `SKILL.md` and `references/*.md`, so the helper scripts and templates are not available there.

## Claude app

Settings -> Capabilities -> Skills -> Upload skill, with the Universal ZIP.

## Local models

Point the system prompt or context loader at `github-release/SKILL.md`.

## Smoke test

> Is my skill repository ready to tag v1.0.0?

A loaded skill states **Mode: Gate** first and reports **Loaded GitHub Release v0.2.0 (SKILL.md at <path>)**.

## Requirements

Python 3.8+, standard library only, for `scripts/check_versions.py` and `scripts/verify_release.py`. Both are read-only and need no network.

## Verify what you downloaded

```bash
sha256sum -c SHA256SUMS.txt
```

MIT licensed - see `LICENSE.txt`.
