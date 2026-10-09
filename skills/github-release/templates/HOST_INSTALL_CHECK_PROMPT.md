# Host install-check prompt — fill <angle> fields, paste into the host, import the report as evidence

Read-only: the host session must change nothing. Import its report into the install log as `Evidence: user-reported` (or `observed` if you watched it run). A failed check is a log row too.

```text
Read-only install check for the <skill> skill, v<version>. Run these tests and report each as PASS/FAIL with what you saw. Change no files.

T1 Arrival line: invoke the skill; quote its loaded report line exactly, including the SKILL.md path it names.
T2 Path check: does that path match the expected install location <expected path>? Name any OTHER copies of this skill you can see (plugin caches, second channels, older dirs).
T3 Version: quote the `metadata.version` line from the loaded SKILL.md file itself (not from a catalog or cache).
T4 Helpers: run each packaged helper with `--version` and quote the output (skip on hosts without a shell; report SKIPPED).
T5 File count: count files in the installed skill folder; expected <n> for this package.
T6 Behavior smoke: answer from the skill only — <one question with a known answer, e.g. "which release ZIP does this host use?">.
Report: one line per test, then the loaded line verbatim.
```

Expected answers come from the release's host matrix and package listing; fill them before sending, and never mark a test PASS that the host did not actually run.
