# Published v1.3.0 host verification

Observed by Codex,2026-10-24. Deliberately prepared public fact summary, not raw logs
or a transcript. Detailed private receipts/replies remain in owner project records.

Both normal fresh CLI hosts load GitHub Release1.3.0 with author Jesse Raber and
repository https://github.com/JesseRaber/github-release. Codex uses the standalone
skills/github-release/SKILL.md path; Claude Code uses the directory-marketplace
local-marketplaces/github-release/skills/github-release/SKILL.md source. Exact
resolved paths were observed in the private host replies and loader traces.

Codex29 and Claude33 installed source files match their exact published archives,
with zero missing/extra/different. Backups were manifest-verified outside discovery
roots. The Claude updater generated a duplicate cache skill; its SKILL.md was
preserved as SKILL.backup-not-loaded.md, then target duplicate checks passed for
both hosts across all configured roots. Future plugin updates require that check.

Each host passed all twelve declared approval/handoff decision cases with actual
loader evidence, without candidate guidance injection. Reasons were manually
reviewed: Claude B still suggests a broader missing approval bundle than the PR
request requires. Preserve that prose caution; structured PASS is not arbitrary
reasoning or reliability certification. No unsafe advancement was observed.

Installed trial hashes equal published assets, so no reinstall was needed after
publication. Desktop picker not tested; fresh CLI loading does not prove a desktop
UI refresh. Other upload hosts are not certified. Existing interactive sessions
should restart to refresh skill lists.
