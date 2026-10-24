# github-release 1.3.0

Release handoffs preserve the owner's scope, verification distinguishes stable and preview releases, and shell examples receive parser-only regression checks.

## Changes

- Handoffs offer explicit prepare-only, PR-only and approved-workflow variants. Original approvals carry forward; later exclusions and mandatory host confirmations remain binding.
- Twelve decision scenarios cover continuation, completed scope boundaries and later narrowing. Candidate-guidance runs remain distinct from installed-host verification.
- Shell-syntax tests parse Bash and PowerShell workflow/example snippets without executing them, including malformed-control and non-execution checks.
- Offline release-list snapshots require an explicit stable or preview channel and pagination confirmation. Published previews, drafts, missing stable releases and incomplete/error responses are reported separately, with no channel or exact-tag fallback.
- Exact-tag asset verification supports an explicit channel guard while retaining hash, author, notes, publication and immutable-release checks.
- Private-edition guidance preserves public history and rights, requires a named pilot and rollback, and reviews sanitized public contributions separately.

## Compatibility and limits

Existing package formats and the MIT license remain unchanged. Finish-Release.ps1 remains stable-only; preview status checks do not add preview publication or automatic installation. Snapshot selection is by publication time within the requested channel, not semantic-version order or GitHub's latest designation. Snapshots do not prove live freshness, access or asset integrity. Parser success does not prove runtime safety. A release does not update installed hosts automatically.
