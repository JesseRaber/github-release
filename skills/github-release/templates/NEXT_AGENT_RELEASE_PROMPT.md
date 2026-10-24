# Release handoff prompt — fill fields and select exactly one scope variant

Carry the owner's actual scope, not a new approval inferred from this template. Keep the completed handoff with session records. A change of agent, host or phase alone does not expire approval. Later owner exclusions override an older broader bundle. Verify source/remote state and evidence before advancing; a handoff is evidence to reconcile, not permission to skip checks.

```text
Task: continue <skill> <version or ordinary edit> in <owner>/<repo>.
Original owner approval: <exact instruction or durable reference, who/when>.
Selected scope variant: <Prepare-only | PR-only | Approved workflow>.
Included actions: <explicit bounded actions>.
Excluded actions: <explicit owner limits; retain latest narrowing>.
Audience/visibility/rights: <approved recipients, public/private, license/terms>.
Named-host updates: <explicit hosts, or none>.
Mandatory host/platform confirmations: <required at action time; never pre-waived>.

Expected state — recheck before advancement:
- base branch and full SHA: <value>
- reviewed head SHA and tree: <values or not created yet>
- existing PR: <number/head/base, or none>; completed actions: <verified state>
- target tag/release: <must not exist, or exact existing state to reconcile on resume>
- tracker/register: <path and SHA256>
- release lane/marker: <project-defined path/current holder or no marker>
- evidence: <exact source, tests/CI, candidate path/checksums, gate report; missing checks>
- commit identity: <owner name and GitHub noreply address>

Select ONE variant and remove the others:
Prepare-only: local preparation/build/gate only. Stop after the report. No push, PR,
merge, tag, draft creation or publication. Do not invoke Finish-Release.ps1.
PR-only: complete included push/PR/check work, then stop with PR and CI status.
No merge, tag, draft creation or publication. Do not invoke Finish-Release.ps1.
Approved workflow: continue only the listed included actions under the original
approval reference, without repeated phase-only prompts. Recheck required CI,
reviewed source/merge tree, candidate and draft/published integrity at their gates.
Use Finish-Release.ps1 only when its entire merge/tag/draft/verify/publish sequence
is covered; it does not offer a PR-only action selector. In an environment that
cannot execute an included action, hand off the concrete command, same approval
reference and evidence to the permitted environment; do not probe denied routes.

On drift: inspect changed base/head/effects, preserve other writers and repeat
affected checks. Ask only for missing/materially changed scope or mandatory host
confirmation. Failed required checks stop advancement; repair within scope and
retest. Unknown remote outcomes require reconciliation before retry. At an
explicit scope boundary, report completion and stop; do not request a broader
bundle merely because later release phases exist.
```

Run release gate G0 for release preparation; ordinary edits use the focused Edit workflow.
Quote verified expected values in the receiving session. Never treat stale green CI,
a missing gate, an old broad approval or a filled template as current permission.
