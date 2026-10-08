---
name: github-release
description: Create GitHub repositories for Agent Skills and release them right the first time - version agreement, a pre-tag gate, deterministic host-specific packages (Claude app, Claude Code, Codex/ChatGPT, Microsoft Copilot, Grok, Gemini Apps, Opal, Antigravity, local models), draft-first publishing, verification of published assets against the local build, and a dated per-host install log. Use whenever an agent prepares, tags, publishes, re-packages or verifies a skill release, sets up a skill repository or release workflow, decides which ZIP a host needs, or records that a skill was uploaded or installed somewhere.
license: MIT
metadata:
  version: "0.1.0"
  repository: https://github.com/JesseRaber/github-release
---

# GitHub Release

A release is right the first time when the bytes you tested are the bytes people download, every host gets a package it accepts, and the record says which host has which version and how anyone knows.

Report as: **Loaded GitHub Release v0.1.0**. State the mode in the first line.

## Choose the mode

| Mode | Typical request | Allowed without further approval | Read |
|---|---|---|---|
| **Setup** | "Make a repo for this skill" | Draft the repository layout and files locally | [repo-setup.md](references/repo-setup.md) |
| **Prepare** | "Get v1.2.0 ready" | Bump versions, write notes, build a local candidate, run checks | [release-gate.md](references/release-gate.md), [packaging.md](references/packaging.md) |
| **Gate** | "Is it ready to tag?" | Read-only checklist against the exact candidate | [release-gate.md](references/release-gate.md) |
| **Publish** | "Release it" | Nothing until the owner approves the exact approval block | [publish.md](references/publish.md) |
| **Verify** | "Check the release" | Read-only: download assets, compare hashes and contents | [verify-and-record.md](references/verify-and-record.md) |
| **Record** | "I uploaded it to Gemini" | Append a host install-log row with its evidence | [verify-and-record.md](references/verify-and-record.md), [host-matrix.md](references/host-matrix.md) |

For "which ZIP do I give host X?" read [host-matrix.md](references/host-matrix.md) only.

## Hard rules

1. **Separate approvals.** Creating a repository, pushing, merging, tagging, creating or publishing a release, changing repository settings and installing into a host are each separate owner approvals. A request to review, build or prepare authorizes none of them. Ask immediately before the action, showing exactly what will happen.
2. **A pushed tag starts a release build.** Gate first, tag second. Never tag a commit whose local candidate build and gate have not passed.
3. **Draft first.** The workflow creates a draft. Verify the draft's downloaded assets against the local candidate, then the owner publishes. A failed draft is deleted and rebuilt; nothing public has to change.
4. **Never replace published bytes.** No `--clobber`, no re-upload, no force-moved tag after publication. A defect in a published release ships as a new patch version. Prefer GitHub immutable releases.
5. **Cite the tag, not `main`.** Evidence about a release comes from the tagged commit and the published assets.
6. **Never disguise code to pass a host scan.** Omit the file from that host's package and document the omission.
7. **Upload acceptance is not behavior.** Record what was observed: accepted, loaded, smoke-tested. Each row needs a date, version, asset hash and evidence type.

## Keep evidence honest

- Say **is** only for what you checked in this session; say **documented as** for repository text, register rows, handoffs and earlier sessions.
- Host rules change without notice. Every host rule carries a date and a source type: observed upload, official documentation (with URL), repository-documented, or inferred.
- A hash match proves only that the compared bytes are equal. Normalized builds (for example CRLF to LF) must say so; do not call them byte-identical.
- If you cannot run a check (no network, no shell, no GitHub access), say which check did not run and what the owner must run instead. Do not report it as passed.

## Helpers

`scripts/check_versions.py` (version agreement, stale versions, workflow safety lint) and `scripts/verify_release.py` (published assets vs checksums, GitHub digests, release state and the local candidate) are read-only, standard-library Python 3.8+, and need no network. Both accept `--version`. Skill repositories keep copies in `packaging/` (see repo-setup.md). Templates for the builder, workflow and records are in `templates/`; some host packages omit them (see host-matrix.md).
