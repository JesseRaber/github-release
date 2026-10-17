# github-release 1.0.0

A dedicated Edit mode handles ordinary GitHub changes alongside the existing skill-release workflow.

## Changes

- Adds Edit mode for ordinary GitHub repository changes, with focused diff review, relevant checks and PR preparation instead of the full skill-release gate.
- Keeps existing release-candidate edits on the Prepare/Gate path so changes cannot inherit stale release evidence.
- Checks automation effects before push, PR changes, merge or queue entry, and preserves separate approval boundaries.
- Verifies CI against the current PR head and base, including merge-test and queue commits, with required checks enforced before merge.
- Updates skill discovery descriptions and checks that linked mode references resolve in all six host packages.

## Compatibility

Existing release modes, helper command interfaces and the six package variants remain available. The version moves to 1.0.0 because the skill version policy classifies a new operating mode as a major change. Time and token savings have not been measured.

## Packages

| Archive | For |
|---|---|
| `github-release-1.0.0-UNIVERSAL-skill.zip` | Claude app, ChatGPT/Codex standalone skills, Antigravity, local models |
| `github-release-1.0.0-claude-code-plugin.zip` | Claude Code plugin |
| `github-release-1.0.0-codex-chatgpt-plugin.zip` | Codex / ChatGPT plugin |
| `github-release-1.0.0-microsoft-copilot-agent-only.zip` | Microsoft Copilot agent, Grok |
| `github-release-1.0.0-gemini-apps-only.zip` | Gemini Spark |
| `github-release-1.0.0-opal-only.zip` | Opal import |

Verify downloads with `sha256sum -c SHA256SUMS.txt`.

## Host installations

Installed host copies are updated separately. A release does not update them automatically; host loading and visible display require checks in each host.

---
Built by [Jesse Raber](https://jesseraber.net) · [YouTube](https://www.youtube.com/@Jesse_Raber)
