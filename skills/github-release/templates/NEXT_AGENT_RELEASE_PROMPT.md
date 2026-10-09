# Release handoff prompt — fill every <angle> field before sending

Copy this into the next agent's chat to hand off a release. The receiving agent runs gate G0 against these values FIRST and refuses on any mismatch — a handoff without expected hashes has produced stale-base release PRs (observed); with them, drift was caught before any work (observed 2026-10-08).

```text
Release task: build and gate <skill> v<version> in <owner>/<repo>. One release lane: refuse if any other release PR or v*-branch is open.

Expected state — verify before any work, stop on mismatch:
- main SHA: <full sha from `git ls-remote origin main`>
- open release PRs: none (or: #<n> is mine to continue)
- tag v<version>: must not exist
- tracker/register file: <path> sha256 <first 12>

Mode: Prepare + Gate only. Tag, draft, publish and settings are separate owner approvals (publish.md).
Candidate goes to: <folder, labeled NOT RELEASED>.
Stop points: after the gate report; before anything that changes GitHub.
```

Keep the filled copy with the session records; the receiving agent quotes which expected values it verified.
