# Changelog

## Unreleased (branch fix/install-backup-shadowing; version not yet assigned)

Install backups can no longer shadow a new install (evidence: multi-agent-folder-cleanup 1.7.1 into Codex standalone, 2026-10-09 — all 22 files matched the release and helpers reported 1.7.1, but Codex loaded 1.7.0 from a backup inside `.codex/skills/_backups/`):

- Rule: backups go beside a host's skills folder, never inside it; otherwise rename the backup's `SKILL.md` to `SKILL.backup-not-loaded.md`. All hosts. New hard rule 8 in SKILL.md.
- Install procedure (verify-and-record.md): required duplicate-name check after every install — exactly one `SKILL.md` with the skill's name, at the new version; more than one is a failed install. Owner restarts the host before the in-host check.
- Record: new `Host load` field — `confirmed in host` only after an in-host check (skill view, "reveal in folder", arrival line); otherwise `files verified; host load not checked`. Install-log template gains the column; check prompt T2 fails on a backup path.
- host-matrix.md: scanned folders and backup locations per host (Codex, Antigravity, Claude Code).
- New helper `scripts/check_skill_duplicates.py` (read-only, standard library) with regression tests, including a backup inside the scanned folder.

## 0.2.1 (draft, not released)

- Gemini Apps package: leave out files without an extension. Gemini's skill uploader rejected 0.2.0 ("The skill folder contains a file with an unsupported file type") because of `templates/gitattributes`; the same package without it was accepted (2026-10-08).
- Builder 1.0.1: new `exclude_no_suffix` key in `packages.json`, plus a host invariant that refuses extensionless files in `gemini-apps-only` regardless of config. Regression test added.
- host-matrix, packaging and INSTALL docs record what Gemini accepted (`.py`, `.json`, `.md`, `.txt`) and the open question of whether scripts run there.

## 0.2.0 (draft, not released)

Portfolio and install lessons (R-023..R-035, R-038..R-040; evidence in the project's 2026-10-08 scan and install records):

- Gate: G0 release-lane-free (one release in flight; expected-main-SHA refusal); fresh clone outside synced folders; G8b executable-bit drift; G8c tag-kind consistency; G11 out-of-repo touch points (`check_versions.py --extra-root`, e.g. a wiki clone); G12 lightweight visual check before public pushes.
- Publish: connector/API pushes can alter bytes — compare pushed blob SHAs with `git hash-object` before the PR; never rename a branch with an open PR (replacement-PR procedure); `--force-with-lease` scope; delete the merged release branch with a recovery SHA after publishing.
- Host matrix: install channels per host (they drift independently; read installed files, never catalog caches); Microsoft Copilot split into Agent Builder vs chat attachment with the ZIP-root question documented open (W-015); Opal/Manus/Copilot sandboxes are review-only — no git work there.
- Record: install procedure (backup with manifest, file-for-file compare incl. zero extra files); `Channel` column in HOST_INSTALL_LOG; new `templates/HOST_INSTALL_CHECK_PROMPT.md` and `templates/NEXT_AGENT_RELEASE_PROMPT.md`.
- Loaded line now names the SKILL.md path, so checks can spot shadow copies.
- Repo setup: auto-delete head branches and social-preview/Website fields as defaults; `safe.directory` note for tool-owned clones.

## 0.1.0 (draft, not released)

- First version: modes Setup, Prepare, Gate, Publish, Verify, Record.
- Draft-first publishing; never replace published bytes; separate owner approvals for each GitHub action.
- `templates/build_packages.py`: config-driven deterministic packager. Reproduced all seven published multi-agent-folder-cleanup v1.6.1 archives byte-for-byte (2026-10-08).
- `scripts/check_versions.py`: version touch points, stale previous-version mentions, release-notes presence, draft-first workflow lint.
- `scripts/verify_release.py`: downloaded assets vs SHA256SUMS, GitHub digests and the local candidate.
- Independent review fixes (2026-10-08): identical archives on Windows and Linux (`create_system` pinned, LF-only `.gitattributes`, CI `same-bytes` job); workflow lint judges each `gh release create`; version patterns no longer match prefixes (1.2.1 vs 1.2.10); host invariants enforced regardless of config; Opal rejects multi-line descriptions; draft metadata fetched from the releases list; `--expect-published` / `--expect-immutable`; CI runs the gate checks and Python 3.8; checkout without persisted credentials.
- Pilot lessons (folder-cleanup v1.6.2, 2026-10-08): where release actions run — tag push, draft publish and settings changes may be refused from cloud sessions and move to the owner's machine; passkey/sudo-mode stop-and-ask; REST per-asset download fallback when `gh release download` (GraphQL) is blocked.
- Dated host matrix (Claude app, Claude Code, Codex/ChatGPT, Microsoft Copilot, Grok, Gemini Apps, Opal, Antigravity, local models).
