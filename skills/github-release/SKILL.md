---
name: github-release
description: v1.1.0 GitHub Release by Jesse Raber. Make ordinary GitHub repository edits through a focused diff, relevant checks and PR workflow; set up and release Agent Skills with version agreement, a pre-tag gate, host-specific packages, draft-first publishing, asset verification and host install records. Use for repository edits or PR preparation, skill repository setup, preparing or verifying a skill release, choosing a host ZIP, or recording an installation.
license: MIT
metadata:
  version: "1.1.0"
  repository: https://github.com/JesseRaber/github-release
---

# GitHub Release

## Distribution intent comes first

Before setup/release preparation, or an edit to ownership/sharing/licensing/promotion, follow [distribution policy](references/distribution-policy.md). Establish the owner-approved audience and rights; keep private work within the owner-selected internal/private audience and authorized accounts/tools and promote public work only within approved scope. Public visibility does not choose a license; never default every project to MIT. Preserve prior grants and third-party notices. This skill's own MIT license is not a license choice for projects it handles.

**Version:** 1.1.0 · **Repository:** https://github.com/JesseRaber/github-release · **Author:** Jesse Raber

A release is right the first time when the bytes you tested are the bytes people download, every host gets a package it accepts, and the record says which host has which version and how anyone knows.

Report as: **Loaded GitHub Release v1.1.0 (SKILL.md at <path you loaded>)**. State the mode in the first line. The path lets install checks detect shadow copies and stale channels.

## Choose the mode

| Mode | Typical request | Allowed without further approval | Read |
|---|---|---|---|
| **Setup** | "Make a repo for this skill" | Draft the repository layout and files locally | [repo-setup.md](references/repo-setup.md) |
| **Edit** | "Fix this README / helper / PR; don't release it" | Inspect, edit and check locally; prepare a diff and PR text | [ordinary-edits.md](references/ordinary-edits.md) |
| **Prepare** | "Get v1.2.0 ready" | Bump versions, write notes, build a local candidate, run checks | [release-gate.md](references/release-gate.md), [packaging.md](references/packaging.md) |
| **Gate** | "Is it ready to tag?" | Read-only checklist against the exact candidate | [release-gate.md](references/release-gate.md) |
| **Publish** | "Release it" | Nothing until the owner approves the exact approval block | [publish.md](references/publish.md) |
| **Verify** | "Check the release" | Read-only: download assets, compare hashes and contents | [verify-and-record.md](references/verify-and-record.md) |
| **Record** | "I uploaded it to Gemini" | Append a host install-log row with its evidence | [verify-and-record.md](references/verify-and-record.md), [host-matrix.md](references/host-matrix.md) |

For "which ZIP do I give host X?" read [host-matrix.md](references/host-matrix.md) only.

For an ordinary repository edit, read **Edit** only; do not load the release gate or build host packages by default. Changes to a helper, workflow or skill instruction still qualify when they are not part of preparing a release candidate. Check the actual branch/PR and project release records: editing an existing release candidate uses **Prepare/Gate** for affected checks, even when the request says only "fix this PR". Run relevant and repository-required checks. Versioned release preparation, distributable packaging, tagging, publication and host installation use their existing modes; a mixed request keeps those actions separate.

## Hard rules

1. **Separate approvals.** Creating a repository, pushing, merging, tagging, creating or publishing a release, changing repository settings and installing into a host are each separate owner approvals. A request to review, build or prepare authorizes none of them. Ask immediately before the action, showing exactly what will happen.
2. **A pushed tag starts a release build.** Gate first, tag second. Never tag a commit whose local candidate build and gate have not passed.
3. **Draft first.** The workflow creates a draft. Verify the draft's downloaded assets against the local candidate, then the owner publishes. A failed draft is deleted and rebuilt; nothing public has to change.
4. **Never replace published bytes.** No `--clobber`, no re-upload, no force-moved tag after publication, no hand-created release. A defect in a published release ships as a new patch version; the published body only gains an appended, dated "Known issues" section. Prefer GitHub immutable releases; every publish approval states whether they are ON or OFF.
5. **Cite the tag, not `main`.** Evidence about a release comes from the tagged commit and the published assets.
6. **Never disguise code to pass a host scan.** Omit the file from that host's package and document the omission.
7. **Upload acceptance is not behavior.** Record what was observed: accepted, loaded, smoke-tested. Each row needs a date, version, asset hash and evidence type.
8. **The owner authors the release; the tag sits on a reviewed merge.** Commits in a release clone use the owner's identity (AI only as a `Co-Authored-By` trailer). Tag only the merge commit of the merged release PR. Notes read as released text: no candidate wording, placeholders, pre-written dates or internal IDs.
9. **Backups never shadow installs.** Never keep a backup inside a folder a host scans for skills; put it beside that folder, or rename its `SKILL.md` to `SKILL.backup-not-loaded.md`. After every install run `scripts/check_skill_duplicates.py` over all of the host's skill folders: exactly one `SKILL.md` may carry the skill's name, at the new version — more than one is a failed install. Tell the owner to restart the host. Matching bytes and `--version` prove the files, not the load: log `files verified; host load not checked` until a check inside the host confirms it (verify-and-record.md).

## Keep evidence honest

- Say **is** only for what you checked in this session; say **documented as** for repository text, register rows, handoffs and earlier sessions.
- Host rules change without notice. Every host rule carries a date and a source type: observed upload, official documentation (with URL), repository-documented, or inferred.
- A hash match proves only that the compared bytes are equal. Normalized builds (for example CRLF to LF) must say so; do not call them byte-identical.
- If you cannot run a check (no network, no shell, no GitHub access), say which check did not run and what the owner must run instead. Do not report it as passed.

## Helpers

`scripts/check_versions.py` (version agreement, stale versions, workflow safety lint), `scripts/verify_release.py` (published assets vs checksums, GitHub digests, release state and the local candidate) and `scripts/check_skill_duplicates.py` (duplicate skill names under host skill folders, after an install) are read-only, standard-library Python 3.8+, and need no network. All accept `--version`. Skill repositories keep copies in `packaging/` (see repo-setup.md). Templates for the builder, workflow and records are in `templates/`; some host packages omit them (see host-matrix.md).
