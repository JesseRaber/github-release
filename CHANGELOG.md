# Changelog

## 0.1.0 (draft, not released)

- First version: modes Setup, Prepare, Gate, Publish, Verify, Record.
- Draft-first publishing; never replace published bytes; separate owner approvals for each GitHub action.
- `templates/build_packages.py`: config-driven deterministic packager. Reproduced all seven published multi-agent-folder-cleanup v1.6.1 archives byte-for-byte (2026-10-08).
- `scripts/check_versions.py`: version touch points, stale previous-version mentions, release-notes presence, draft-first workflow lint.
- `scripts/verify_release.py`: downloaded assets vs SHA256SUMS, GitHub digests and the local candidate.
- Independent review fixes (2026-10-08): identical archives on Windows and Linux (`create_system` pinned, LF-only `.gitattributes`, CI `same-bytes` job); workflow lint judges each `gh release create`; version patterns no longer match prefixes (1.2.1 vs 1.2.10); host invariants enforced regardless of config; Opal rejects multi-line descriptions; draft metadata fetched from the releases list; `--expect-published` / `--expect-immutable`; CI runs the gate checks and Python 3.8; checkout without persisted credentials.
- Dated host matrix (Claude app, Claude Code, Codex/ChatGPT, Microsoft Copilot, Grok, Gemini Apps, Opal, Antigravity, local models).
