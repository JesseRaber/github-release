# SKILL-NAME X.Y.Z

<!-- Public text: it becomes the release body and is shown as written. Lint (check_versions.py) FAILs on
     status wording ("(candidate)", "not released", "not committed"), TBD/TODO, placeholders, empty
     bullets and pre-written dates like "Released 2026-01-01" — GitHub shows the real publish date.
     Describe changes in product terms. Internal IDs (tracker rows, session UUIDs) go in the PR body. -->

## Changes

- 

## Packages

| Archive | For |
|---|---|
| `SKILL-NAME-X.Y.Z-UNIVERSAL-skill.zip` | Claude app upload, ChatGPT/Codex standalone skills, Antigravity, local models, any skills folder |
| `SKILL-NAME-X.Y.Z-claude-code-plugin.zip` | Claude Code `/plugin install` |
| `SKILL-NAME-X.Y.Z-codex-chatgpt-plugin.zip` | Codex / ChatGPT plugin |
| `SKILL-NAME-X.Y.Z-microsoft-copilot-agent-only.zip` | Microsoft Copilot agent upload, Grok |
| `SKILL-NAME-X.Y.Z-gemini-apps-only.zip` | Gemini Spark upload (check whether your Gemini surface accepts scripts) |
| `SKILL-NAME-X.Y.Z-opal-only.zip` | Opal import |

Verify downloads with `sha256sum -c SHA256SUMS.txt`.

## Publication boundary

Installed host copies are updated separately; this release does not change any host by itself.
