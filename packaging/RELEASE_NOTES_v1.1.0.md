# github-release 1.1.0

Distribution guidance now distinguishes intentionally public skills from private or owner-controlled work.

## Changes

- Adds an owner-approved audience and rights check before repository setup, release preparation, and edits to licensing or sharing.
- Keeps private work within its approved internal users, organizations and AI accounts/tools, with no public promotion or storefront material.
- Makes public discovery descriptions, documentation, attribution and approved links conditional on intentional public distribution.
- Removes the universal MIT default. Public repository visibility does not select a license; prior grants and third-party notices remain in force.
- Checks source, package notices, destinations and visibility for consistency without claiming copy protection or changing access permissions.

## Compatibility

Edit and release modes, helper interfaces and all six host variants remain available. This public skill retains its existing MIT license. The new distribution prerequisite is a minor-version change under the existing version policy. It does not change other projects, grant sharing rights or update installed hosts automatically.

## Packages

| Archive | For |
|---|---|
| `github-release-1.1.0-UNIVERSAL-skill.zip` | Claude app, ChatGPT/Codex standalone skills, Antigravity, local models |
| `github-release-1.1.0-claude-code-plugin.zip` | Claude Code plugin |
| `github-release-1.1.0-codex-chatgpt-plugin.zip` | Codex / ChatGPT plugin |
| `github-release-1.1.0-microsoft-copilot-agent-only.zip` | Microsoft Copilot agent, Grok |
| `github-release-1.1.0-gemini-apps-only.zip` | Gemini Spark |
| `github-release-1.1.0-opal-only.zip` | Opal import |

Verify downloads with `sha256sum -c SHA256SUMS.txt`.

## Host installations

Installed host copies are updated separately. A release does not update them automatically; host loading and visible display require checks in each host.

---
Built by [Jesse Raber](https://jesseraber.net) Â· [YouTube](https://www.youtube.com/@Jesse_Raber)
