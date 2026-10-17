# Ordinary GitHub edits

When editing ownership, license, sharing or promotion text, also read [distribution-policy.md](distribution-policy.md). Carry the current owner-approved scope into the local diff; an ordinary edit does not authorize public sharing or change access.

Use **Edit** for a repository change or PR without a release: documentation, code, tests, skill instructions or workflow maintenance. Prepare a reviewable change and verify it through the last authorized boundary. Do not run G0-G14, bump versions or build host packages solely because the repository contains a skill.

## 1. Establish the change

Read the repository's applicable instructions and current task/PR records. Confirm canonical repository, base branch and commit, requested outcome, and whether another writer or PR already covers it. Reuse completed work after checking the current source. Preserve unrelated edits; if the checkout is a mirror or has mixed changes, use an isolated checkout and transfer only the requested diff. Do not reset or stash someone else's work.

Classify the actual work, not just the request's wording or branch name. If the branch/PR is an existing release candidate, or the edit changes its versioned source, notes or assets, use [Prepare/Gate](release-gate.md) to reassess affected evidence and the release lane/marker before any authorized push. A small fix cannot retain a gate PASS for changed candidate bytes. Reuse only checks whose exact covered surface still matches; tag-target, draft and published-asset integrity checks still run at their own boundaries. Without current release/PR records, report the classification as unchecked and keep the work local until resolved.

Record the allowed stopping point: local review, approved push, approved PR, or approved merge. Follow the owner's current authorization and project rules. Pushing, opening a PR, merging, changing settings, tagging, publishing and installing are distinct actions; local preparation grants none of them. Honor an explicit local-only instruction even if tools can write remotely.

## 2. Edit and check the affected surface

Make the smallest complete change. Inspect the full diff against the recorded base, including added/untracked files, deletions, generated output, file modes and unexpected changes. In Git start with `git status --short`; inspect both staged and unstaged patches and their whitespace/stat/mode checks, plus the actual contents of untracked files (ordinary `git diff` omits them). A clean whitespace check alone is not a review.

Choose checks by the behavior affected, plus all checks the repository requires:

| Change | Relevant local evidence |
|---|---|
| Documentation | Links/anchors and examples resolve; inspect a rendered page when layout or diagrams changed |
| Code or helper | Tests for affected behavior and failure paths; required lint/type checks |
| Skill instructions | Realistic requests route correctly, preserve approval limits and load the needed references |
| CI/workflow | Parse/lint supported syntax; review event triggers, permissions, command safety and affected jobs; run the called checks where available |
| Packaging/build configuration | Validate affected layouts and outputs; build affected packages when needed to check the edit, labeling them local validation material |

Capture each command/check and its actual exit code or observation. `not-run` and an environment-blocked check are not passes. Previously recorded evidence applies only to unchanged source/configuration it actually covered; cite its commit/hash and date. Rerun anything the new diff can affect. A local workflow review is not a GitHub CI run.

Changing release automation does not authorize executing it. Before an authorized push, PR change, merge, queue entry or workflow rerun, inspect the automation it can trigger, including called workflows/scripts. A merge to the default branch may deploy, tag or publish even when no release command is run by the agent. Identify these effects in the approval scope and stop before the triggering action if they are not authorized. Treat unavailable automation details as unchecked. Do not disable required repository checks to make Edit appear shorter.

## 3. Prepare or verify the PR boundary

For local-only work, stop with the diff, check results and proposed PR title/body. Remote writes and CI for the local changes are **not-run**; distinguish any read-only observations of an existing remote PR/base. No commit is needed merely to show a reviewable diff.

When the corresponding action is authorized:

1. Re-read the base and existing PR immediately before writing; reconcile changes that affect the edit or evidence. Commit only the intended files with the project's required identity; inspect the resulting commit. Before push, present its repository, destination branch, exact commit and known automation effects. Never force-push or write directly to the default branch without explicit scope for that action.
2. After push, read the remote branch SHA and compare it with the expected commit; verify changed remote blobs against the reviewed contents. A successful command or a missing shallow-clone tracking ref is insufficient evidence either way.
3. Before opening/updating a PR, review its head, base, title and body. After the approved write, read them back and inspect the complete diff. A REST fallback must preserve the same reviewed fields. Attach a created PR to the chat when the host supports it.
4. Bind CI evidence to the current PR head and base: record the actual tested SHA and event. A pull-request merge-test commit or merge-queue commit can differ from the head SHA; verify its relationship to the current head/base rather than accepting arbitrary green CI or rejecting it solely for a different SHA. Distinguish passed, failed, pending, skipped and not-run; report missing required checks. A changed head or base requires reassessing the diff, applicable reviews and affected checks. Never rerun a workflow with external side effects without the required authorization.
5. Stop before merge unless separately approved. Immediately before an approved merge, re-read head/base, required review/check results, unresolved conflicts and automation effects. Failed, pending, missing, skipped or not-run required checks are not a passing merge prerequisite. Do not bypass protections or enable auto-merge merely to skip this boundary. If the approved diff/head or effects changed, obtain approval for the changed scope. For a merge queue, distinguish pre-entry checks from queue-only checks generated after enqueue: entry requires approval covering the eventual automated merge and its effects, plus passing pre-entry requirements; the queue-only checks must pass on the verified queue commit before merge. After merge, verify the resulting base-branch commit/tree and relevant checks, and report actual deployments/publication/install effects separately from the merge itself. An ordinary merged PR is not automatically the reviewed release PR required for tagging in [Publish](publish.md).

If access is blocked, retain the local patch and exact remaining action/check. Do not switch accounts or transports to bypass an authorization refusal.

## 4. Compact result and measurement

Report only what this edit needs:

```text
Edit: <outcome and changed files>
Base: <canonical repo, branch, commit>; local diff or commit: <reference>
Checks: <commands/observations, exit codes, limitations>
Remote: <verified branch SHA/PR/CI for exact head, or not-run: local-only>
Boundary: <completed action>; remaining: <next action and authorization needed>
```

When evaluating R-078 efficiency, record start/end times with offsets, workflow steps/tool calls and owner round trips, checks reused with their source, and defects found. Use token counts only when the runtime exposes reliable counts. Label synthetic/local scenarios as such. Compare comparable real edits before claiming time or token savings; shorter instructions alone do not establish savings.

## When to change modes

- A docs-only PR remains Edit even in a skill repository. Existing required CI may still build packages; keep it enabled.
- A helper fix or release-workflow repair outside an existing release candidate remains Edit; test the affected behavior and safety properties. A fix to a release candidate must revalidate its affected Prepare/Gate evidence.
- "Prepare the next version", rebuild distributable host ZIPs, tag or publish: use Prepare/Gate/Publish/Verify as applicable. Keep all tag-target, draft and published-asset integrity checks. Edit evidence is not a release gate result.
- An installation or host-log request uses Record/Verify and the install rules. A mixed request completes only the authorized portion and states the remaining boundary.
