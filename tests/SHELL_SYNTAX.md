# Parser-only shell regression checks

Run the repository suite with `python -m unittest discover -s tests -v`.
Existing CI runs it on Windows and Linux, including Python 3.8. Bash and
PowerShell 7 (`pwsh`) are required: a missing parser fails, never silently skips.
On Windows the checker prefers Git for Windows Bash over the WSL launcher.
Print the source/line inventory with `python tests/shell_syntax.py`.

The inventory covers `.github/workflows/*.yml`/`.yaml`, the skill's workflow
templates, labeled Bash/sh/shell/PowerShell/pwsh and YAML fences in skill
Markdown and the root README, and skill `.ps1`/`.sh` files. Unlabeled/text
fences, other languages, external projects and historical release notes are
outside this inventory. Current coverage: 40 snippets, 38 Bash and 2 PowerShell.

Bash uses `--noprofile --norc -n` with startup-injection environment variables
removed. PowerShell uses its language Parser API with `-NoProfile`, never
invokes or sources the candidate. Sentinel controls verify neither snippet
executes. Malformed controls reject extra/missing `fi` and unclosed braces.

Workflow extraction supports literal run blocks and inline quoted/plain runs,
step shell fields before/after run, Linux implicit Bash and Windows implicit
PowerShell. Dynamic runners require explicit shell. Defaults, flow mappings,
folded/alias/tagged runs and custom shells require reviewed extractor support
and currently fail. Heredoc indentation is retained. Extraction is constrained,
not a general YAML parser, action validator or shell sandbox.

Workflow expressions are replaced with inert values; their runtime expansion
and quoting safety are not proved. Angle-bracket example fields are replaced
only in documentation, never actual workflow scripts. Tests check that real
workflow redirections remain visible to the parser. Documentation placeholders
still need real values before use. Parser success proves grammar for the checked
snippet only, not command availability, credentials, GitHub semantics, release
integrity or authorization. Existing release gates remain required.
