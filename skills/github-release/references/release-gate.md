# Prepare and gate a release

Use in **Prepare** (make the candidate) and **Gate** (judge it, read-only). The gate result is a list of checks with pass, fail or not-run, not a summary.

## 1. Version touch points

A skill version appears in more places than CI usually checks. List them in `packaging/version_files.json` (template in `templates/`) and run:

```bash
python packaging/check_versions.py --repo . --version 1.2.0 --previous 1.1.0
```

Typical touch points:

- `skills/<name>/SKILL.md` frontmatter `metadata.version` (source of truth)
- `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` `version`
- every helper script's `__version__` / version constant
- "Report as: Loaded ... vX" line in SKILL.md
- install guides' "Expected loaded version"
- README "What vX adds", reference docs that name the version
- tests that assert the version
- `packaging/RELEASE_NOTES_vX.Y.Z.md` (must exist; the workflow refuses to publish without it)
- `CHANGELOG.md` entry

`--previous` lists every remaining mention of the old version outside history files (CHANGELOG, older release notes). Each one is either a stale reference to fix or history to leave; decide per line. (Observed failure: a Copilot install guide still said the previous version after a release.)

## 2. Build the local candidate

Build from a **fresh clone of the canonical repository, outside any synced folder** (`%USERPROFILE%\dev\<repo>` or a temp dir, never inside OneDrive/SharePoint), cloned with `core.autocrlf=false`. Observed failures from clones inside synced project folders: `.git/index.lock` conflicts, read-only dirs that cannot be removed, stale copies that no longer match the remote (2026-10-06, folder-cleanup and cabinet-load-optimizer records). A project folder's copy of the repo is documentation, not a build source.

```bash
python packaging/build_packages.py ../candidate-1.2.0 --status "local candidate, not published"
```

- Output goes to a new folder outside the repository, labeled as a candidate.
- Keep `BUILD_EVIDENCE.json` and `SHA256SUMS.txt` from this build; the verify step compares the published draft against them.
- Never put a same-version candidate beside released packages without an unmistakable label (`CANDIDATE - not released`). A candidate ZIP uploaded to a host by mistake is a real, observed failure.

## 3. Gate checklist

Run in order. Stop at the first fail.

| # | Check | How |
|---|---|---|
| G0 | Release lane is free: no other open release PR; no `v<version>-*` branch by another writer; the expected `main` SHA (from the handoff prompt, when one exists) still equals the remote | `gh pr list --state open`; `git ls-remote --heads origin`; `git ls-remote origin main`. One release in flight per repo — observed collision 2026-10-08: two agents built "v1.6.2" from different bases; the loser's PR had to be renumbered |
| G1 | Working tree clean; candidate built from the exact commit to be tagged, in a fresh clone outside synced folders (section 2) | `git status --porcelain` empty; record `git rev-parse HEAD` |
| G2 | Versions agree; no unintended stale versions | `check_versions.py` exit 0 |
| G3 | Release notes file exists for this version | `check_versions.py` |
| G4 | Workflow is draft-first and never clobbers | `check_versions.py --workflow .github/workflows/release.yml` |
| G4b | Windows and Ubuntu builds give identical archives | CI `same-bytes` job (template ci.yml) |
| G5 | CI green on this commit, including Windows if helpers run on Windows | CI run link |
| G6 | Skill validators pass (frontmatter, name matches folder, description <= 1024 chars; OpenAI skill/plugin validators pinned by commit) | CI or local run |
| G7 | Candidate built, every archive byte-verified, packaged scripts smoke-tested | builder output; no warnings left unexplained |
| G8 | Line endings: `.md`/`.py` are LF in the repository (`.gitattributes`); no CRLF in the Opal package | builder asserts Opal; `git ls-files --eol` |
| G8b | No unintended executable bits (mode drift between OSes is real: 3 files went 100755 on Linux while Windows kept 100644, folder-cleanup v1.6.1) | `git ls-files -s \| grep ^100755` lists only intended scripts |
| G8c | Tag kind matches the repository's convention — mixed lightweight/annotated tags break `v<tag>^{}` peeling and citation | `git cat-file -t v<previous>` (expect `tag` for annotated) |
| G9 | Each host package matches host-matrix.md rules for this release | compare package listing with Table A |
| G10 | Tag does not exist yet locally or remotely | `git ls-remote --tags origin vX.Y.Z` empty |
| G11 | Out-of-repo version touch points: the wiki (`<repo>.wiki.git`), marketplace listings and host store descriptions name the new version or are explicitly listed as not-run | `check_versions.py --previous X.Y.Z --extra-root ../wiki-clone`; anything unreachable gets a `not-run` line, never a silent pass |
| G12 | Visual check before a public push: README renders (tables, any diagram), links and image alt text are current, and the social-preview image is not contradicted by this release's content. Update assets only when content changed | open the rendered README on the branch; repository settings → social preview (owner) |

## 4. Windows lessons (observed)

- Clone with `core.autocrlf=false`; `git am` failed with `autocrlf=true`. The template `.gitattributes` forces LF for all text so Windows and Linux builds match.
- A local candidate is only comparable to the CI build if both use the same builder version; the builder pins ZIP metadata (`create_system`) so the OS does not change the bytes. Different zlib versions could still change compressed bytes; if a candidate differs only that way, compare member contents and record it. When the owner's machine and CI run different OSes and bytes still differ, the comparable candidate is the **CI artifact of the gated commit** (download it from the CI run) rather than the laptop build.
- If `git status` reports "dubious ownership" (clones inside tool-owned dirs such as `~/.codex/...`), use `git -c safe.directory=<absolute path>` for that clone only; never set `safe.directory=*`.
- Child-process stdout is cp1252 on Windows; helpers must write UTF-8 safely.
- Do not write shared text files with Windows PowerShell 5.1 (BOM/ANSI). Preserve a BOM only where a file already needs one.
- Do not retype large files through chat tools; copy or apply patches.

## 5. Gate report format

```text
Gate: <skill> v<version> at <commit>  —  PASS | FAIL | INCOMPLETE
G1 pass  clean tree, HEAD 1a2b3c4
G5 not-run  no CI access in this session; owner to confirm run <link>
...
Candidate: <folder>, SHA256SUMS sha256 <first 12>
```

INCOMPLETE is not PASS. Do not propose a tag on INCOMPLETE.
