# Approval scope and continuation

Carry an explicitly approved, defined workflow through its included steps without renewed approval merely because the phase changes. Record the target, bounded changes/actions, audience, data destinations, endpoint and exclusions once; reuse that scope while it remains valid. Continue ordinary validation, waiting, safe retries and in-scope corrections. Reconcile uncertain outcomes before retrying; never blindly repeat a possibly completed action. A review or preparation request does not authorize publication, installation or sending. Ask only for essential missing information, materially changed scope, visibility, audience or data destination, withdrawn approval, or mandatory host confirmation. Failed checks block advancement: repair within scope or report the genuine blocker and continue independent authorized work. Destructive operations, security/access changes and new disclosure need explicit scope and any required action-time confirmation. Host policies and denials remain binding; this guidance does not disable them. Stop at the agreed endpoint.

## Record once, verify at each boundary

Reuse sufficient authorization already supplied by the owner. If scope is missing, prepare a concrete reviewable result first and ask once for the missing bundle. Distinct actions need explicit coverage, not distinct conversation rounds.

```text
Repository/account: <exact owner/repo and account>
Base/branch: <branch, observed SHA; permitted changes and endpoint>
Included actions: <commit/push/PR/CI repair/merge/tag/draft/verify/publish>
Version/tag: <exact version and tag, or not applicable>
Artifacts: <package names, source manifest and build process>
Audience/visibility/licensing: <approved recipients, rights, destinations>
Automation effects: <CI, deploy/release triggers and merge queue effects>
Immutable releases: <ON/OFF, source/time and consequences>
Optional actions explicitly included: <named-host installs; exact branch cleanup>
Excluded: <settings/access/credentials, force push, deletion, spending,
           other repositories, new audience or data destinations unless listed>
Approval evidence: <owner statement and scope reference>
```

Bind later commit/merge SHAs and artifact hashes to the approved bounded diff and deterministic workflow as they become known. A newly computed SHA alone does not require another prompt; altered content, effects or audience require reassessment. Re-read current source/PR/remote state before writing; preserve concurrent work, required reviews/protections, exact merge/tag checks, draft-first checks and immutable published bytes. Passing validation is evidence, not permission. Pending CI is a wait; failed required checks prevent advancement.

For a transient failure, inspect the actual remote outcome before retrying. If an action may have completed and cannot be reconciled, stop that action and report uncertainty. Do not bypass a denial using another account, transport or helper. Required host/security/irreversible-action confirmations remain action-time requirements even when ordinary workflow steps were bundled. When the session cannot perform merge, tag or publish, the single owner run of `scripts/Finish-Release.ps1` carries out the remaining approved steps. Its typed confirmation is the owner's action-time approval for exactly the listed steps; plan it in the first approval instead of discovering each refusal in turn.

Finish with actions completed, exact source/artifacts/check evidence, scope exceptions and remaining work. Source changes and file installation do not prove fresh-host prompt behavior; measure approval rounds in a permitted fresh-host trial before claiming runtime improvement.
