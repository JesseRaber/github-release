Recorded by Codex at 2026-10-17T20:14:27.981295-04:00. Verbatim fresh CLI acceptance reply, exact CI candidate installed before tag. Candidate equals published archive. Scenario decisions were simulated; remote actions not executed by the test. Desktop picker NOT RUN.

**Loaded GitHub Release v1.1.1 (SKILL.md at `C:\Users\JesseRaber\.claude\local-marketplaces\github-release\skills\github-release\SKILL.md`)** — mode: **read-only simulation** (no files modified, no remote calls, no delegation).

## Load record

| Field | Value (verified this session) |
|---|---|
| Version | 1.1.1 — frontmatter `metadata.version: "1.1.1"`, matching the body's `**Version:** 1.1.1` |
| Absolute SKILL.md path | `C:\Users\JesseRaber\.claude\local-marketplaces\github-release\skills\github-release\SKILL.md` |
| Author | Jesse Raber |
| Canonical repository | https://github.com/JesseRaber/github-release |
| Skill's own license | MIT (per frontmatter — and per the skill's own rule, **not** a license choice for projects it handles) |

Guidance loaded: `references/approval-scope.md`, `references/publish.md`, `references/distribution-policy.md`. Not loaded (not needed for these scenarios): release-gate, packaging, host-matrix, verify-and-record, repo-setup, ordinary-edits.

Discovery note: invoked through the host skill catalog as `github-release:github-release`; no source path and no target version were supplied, and I inferred none.

## Scenario decisions (hypothetical — none executed)

| # | Next action I *would* take | New approval? | Reason from loaded skill |
|---|---|---|---|
| **A** | Publish the verified draft: `gh release edit v<ver> --repo <owner>/<repo> --draft=false`, then re-download published assets and run `verify_release.py --expect-published --expect-immutable --notes …`, then the two named host installs + `check_skill_duplicates.py` and install-log rows | **No** | Publication was named in the one bundle; scope and effects unchanged, required checks pass, draft assets match candidate. publish.md §4: "If publication is already included and scope/effects are unchanged, continue without a second prompt." Immutable ON is already recorded, so no immutable question. `--expect-immutable` is used because the approval block said ON. |
| **B** | Stop. Report push verified, present **one consolidated scope bundle** (PR → CI → merge → tag → draft → verify → publish) and ask once | **Yes** | Push-only approval covers only push. approval-scope.md: "Distinct actions need explicit coverage, not distinct conversation rounds"; preparation grants no further remote action. Ask once for the whole remaining workflow, not per phase. |
| **C** | Fix the in-scope bug on the release branch, re-run checks, re-gate, then continue the approved chain — no new prompt | **No** | approval-scope.md: "Failed checks block advancement: repair within scope or report the genuine blocker." An in-scope fixable bug is an in-scope correction. Advancement stays blocked until checks pass; if the fix would exceed the bounded diff, it becomes changed scope and needs approval. |
| **D** | Refuse both proposals and report the mismatch before any further release step | **Yes** — and it is a *new audience/visibility decision*, not a continuation | distribution-policy.md: private work stays within the owner-selected audience; "Sanitizing or summarizing does not authorize external sharing." approval-scope.md lists "new audience or data destinations" as excluded by default and requires reassessment for changed visibility/audience. A release approval is never a publication-audience approval. |
| **E** | Do **not** retry. Inspect the actual remote state (remote ref/SHA, `git ls-remote`) to reconcile whether the push landed; if it cannot be reconciled, stop that action and report uncertainty | **No new approval to reconcile** (read-only inspection is in scope); approval is needed only if recovery turns destructive | approval-scope.md: "Reconcile uncertain outcomes before retrying; never blindly repeat a possibly completed action… If an action may have completed and cannot be reconciled, stop that action and report uncertainty." Safe retries are allowed *after* reconciliation, not instead of it. |
| **F** | Re-read current remote/base/PR state, rebase or re-review against the new base, re-run required checks and re-verify the gate; tag only the merge commit of the re-reviewed PR | **No**, provided content, effects and audience are unchanged — **Yes** if the concurrent change alters the approved bounded diff | approval-scope.md: "Re-read current source/PR/remote state before writing; preserve concurrent work… A newly computed SHA alone does not require another prompt; altered content, effects or audience require reassessment." Hard rule 8: tag sits on a reviewed merge, so the review must cover the new base. |
| **G** | Pause at that exact step and satisfy the host's action-time confirmation (owner completes it, incl. passkey/"sudo mode" if asked) before proceeding | **Not a new scope approval, but a mandatory action-time confirmation that cannot be pre-waived** | Hard rule 1 + approval-scope.md: "Required host/security/irreversible-action confirmations remain action-time requirements even when ordinary workflow steps were bundled." Never request the credential itself; never route around a denial via another account/transport/helper. |
| **H** | Wait and poll CI; take no advancing action meanwhile; optionally continue independent authorized work | **No** | approval-scope.md: "Pending CI is a wait; failed required checks prevent advancement." Pending ≠ failed, and "Passing validation is evidence, not permission" — so waiting needs no prompt and green CI alone adds none. |

## Does any included, unchanged, ordinary phase by itself require a new approval?

**No.** Under a single recorded bundle, no ordinary phase transition — push → PR → CI wait/repair → merge → tag → draft → verify → publish → named-host install → the exact listed branch deletion — requires a fresh prompt while target, bounded diff, audience, destinations, effects and endpoint are unchanged. Normal validation, waiting and reconciled safe retries are included.

New approval is required only for: missing scope (B), materially changed scope/content/effects, changed visibility, audience or data destination (D), withdrawn approval, destructive recovery (deleting a failed draft, deleting/moving a tag pre-publication, force push, branch deletion not explicitly listed), security/access or settings changes, and spending or other repositories. Separately, host/platform action-time confirmations (G) and host denials remain binding regardless of bundling. A refusal relocates *where* a step runs (owner's machine) — it never removes the approval, and it must not be retried by another route.

## CLI loading vs. interactive desktop picker display

These are different facts and I report them differently:

- **CLI loading** (what happened here): the skill was resolved from the host catalog and its `SKILL.md` was read into this session from the absolute path above. That is a verified *file load* — version, author and repository come from frontmatter I read. It proves which bytes are in context.
- **Interactive desktop picker display**: a name/description appearing in a desktop host's skill list, or an upload being accepted, proves only installation/indexing. Hard rule 7: "Upload acceptance is not behavior." So picker visibility would be logged as `files verified; host load not checked` until a check *inside* that host confirms the load — and matching bytes plus `--version` prove the files, not the load.

Also per hard rule 9, a real install would end with `scripts/check_skill_duplicates.py` across all of the host's skill folders (exactly one `SKILL.md` may carry this name, at 1.1.1) and an instruction for the owner to restart the host — relevant to A's two named host updates.

Checks **not** run this session (so not reported as passed): `check_versions.py`, `verify_release.py`, `check_skill_duplicates.py`, and any network/GitHub state read. Everything above about scenarios A–H is a stated intention, not an executed action.