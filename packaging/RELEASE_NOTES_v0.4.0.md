# github-release 0.4.0

This release makes the installed skill's identity easier to inspect and makes release-gate reports more precise.

## Changes

- The skill source description and body identify version 0.4.0, the canonical GitHub repository and author Jesse Raber. Plugin and marketplace descriptions include the version and author; their actual host displays require separate checks.
- Release preparation can cite prior evidence for an unchanged source and checked surface. Changed files or settings require affected checks to run again; tag, draft and published assets are verified at their own boundaries.
- Gate reports distinguish live wiki and host-store state from local mirrors, record justified repository template differences separately from unresolved drift, and show an allowed skipped host trial as an explicit overall exception.
- Procedure guidance covers executable-mode drift during device copies, REST PR creation when GraphQL is blocked, immutable-release setting checks and shallow-clone tracking-ref reports.

## Packages

| Archive | For |
|---|---|
| `github-release-0.4.0-UNIVERSAL-skill.zip` | Claude app upload, ChatGPT/Codex standalone skills, Antigravity, local models, any skills folder |
| `github-release-0.4.0-claude-code-plugin.zip` | Claude Code `/plugin install` |
| `github-release-0.4.0-codex-chatgpt-plugin.zip` | Codex / ChatGPT plugin |
| `github-release-0.4.0-microsoft-copilot-agent-only.zip` | Microsoft Copilot agent upload, Grok |
| `github-release-0.4.0-gemini-apps-only.zip` | Gemini Spark |
| `github-release-0.4.0-opal-only.zip` | Opal import |

Verify downloads with `sha256sum -c SHA256SUMS.txt`.

## Publication boundary

Installed host copies are updated separately; this release does not change any host by itself.

---
Built by [Jesse Raber](https://jesseraber.net) · [YouTube](https://www.youtube.com/@Jesse_Raber)
