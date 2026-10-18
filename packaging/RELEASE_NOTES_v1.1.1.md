# github-release 1.1.1

An approved release workflow can now continue through its agreed steps without repeated approval prompts.

## Changes

- Records one explicit scope for the repository, changes, audience, artifacts and intended actions.
- Reuses sufficient approval across push, PR, CI, merge, tag, draft verification and publication when those steps are included.
- Preserves local-only and push-only boundaries, required checks, reviewed merges, draft-first verification and immutable release bytes.
- Stops for material scope changes, unresolved failures, uncertain action outcomes and mandatory host/security confirmations.
- Aligns Setup, Edit, Publish, distribution guidance, README and release handoff text.

## Compatibility

This is an instruction correction. Modes, helper interfaces, six host formats and the existing MIT license are unchanged. Approval to prepare alone still grants no remote action. A release does not update installed hosts automatically.

## Packages

| Archive suffix | Host |
|---|---|
| UNIVERSAL-skill | Claude app, Codex standalone, Antigravity, local models |
| claude-code-plugin | Claude Code plugin |
| codex-chatgpt-plugin | Codex / ChatGPT plugin |
| microsoft-copilot-agent-only | Microsoft Copilot agent, Grok |
| gemini-apps-only | Gemini Spark |
| opal-only | Opal import |

Verify downloads with SHA256SUMS.txt. Installed loading and displayed identity require separate host checks.

Built by [Jesse Raber](https://jesseraber.net) - [YouTube](https://www.youtube.com/@Jesse_Raber)
