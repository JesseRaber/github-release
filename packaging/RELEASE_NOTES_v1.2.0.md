# github-release 1.2.0

An approved release can continue through an owner-run helper when the current session cannot perform the remaining actions.

## Changes

- New `scripts/Finish-Release.ps1` for the owner's machine. After one typed approval it merges the release PR, tags the merge commit, waits for the workflow's draft, verifies every asset against the gated checksums, publishes, re-verifies, files the assets.
- It stops at the first failed check, never overwrites a different file, skips steps already done when re-run, and writes a log and JSON receipt the agent can read.
- Publish guidance and approval scope now plan merge, tag push and publish as that single owner run from the first approval.

- Checks include the reviewed head/base, successful required CI, merge-tree identity, exact-tag workflow, approved audience/immutable policy, reviewed notes and asset hashes. Skipped checks are not passes.
- Arbitrary post-release commands are excluded; named-host installation remains separately verified within its approved scope.

## Compatibility

Existing modes, Python helpers, host formats and the MIT license are unchanged. The script needs PowerShell 7, `git` and a signed-in GitHub CLI. Copilot and Gemini packages omit `.ps1` files as before. Approval to prepare still grants no remote action, and a release does not update installed hosts automatically.

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
