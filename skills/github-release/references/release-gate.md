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

### Which number to bump

Decide by rule, not by asking each time. Name the level and the item that triggered it in the gate report.

| Level | When |
|---|---|
| **patch** (1.2.0 → 1.2.1) | text and documentation fixes; bug fixes that leave helper output and package layout unchanged |
| **minor** (1.2.0 → 1.3.0) | a new helper flag or helper; new output lines or columns; changed output meaning; a new gate check or lint that can fail a run that passed before; a package added or removed; a new host |
| **major** (1.x → 2.0.0) | a mode or protocol change, or a helper interface that breaks existing callers |

The highest level among the release's changes wins. Owner override is allowed and recorded.

`--previous` lists every remaining mention of the old version outside history files (CHANGELOG, older release notes). Each one is either a stale reference to fix or history to leave; decide per line. (Observed failure: a Copilot install guide still said the previous version after a release.)

## 2. Build the local candidate

Build from a **fresh clone of the canonical repository, outside any synced folder** (`%USERPROFILE%\dev\<repo>` or a temp dir, never inside OneDrive/SharePoint), cloned with `core.autocrlf=false`. Observed failures from clones inside synced project folders: `.git/index.lock` conflicts, read-only dirs that cannot be removed, stale copies that no longer match the remote (2026-10-06, folder-cleanup and cabinet-load-optimizer records). A project folder's copy of the repo is documentation, not a build source.

In every fresh clone, before the first commit, set the owner's identity so release commits are attributed to the owner, not to an AI:

```bash
git config user.name  "<owner name>"
git config user.email "<owner's GitHub noreply address, e.g. 12345+owner@users.noreply.github.com>"
```

AI attribution goes only in a commit trailer (`Co-Authored-By: ...`), never in the author field. Observed: release commits authored "Claude <noreply@anthropic.com>" showed no owner link on GitHub.

**Never hold a candidate only in a sandbox.** Before building, either push the candidate branch or save `git bundle create <project scratch>/<branch>.bundle main..<branch>` (full history with `--all` when the base may move). Observed: a worktree was lost before it was pushed and its notes had to be rebuilt from a draft.

**Synced clones are inspect-only.** When you must read a clone inside OneDrive/SharePoint or through a device bridge, use `git --no-optional-locks -c core.fsmonitor=false status` so the read leaves no `.git/index.lock` (observed: a read-only `git status` through a bridged OneDrive path left a lock the mount could not delete). After every write through a bridge or connector, re-hash the written file at its destination; a bridged write was observed to land a stale copy first.

**Run tests on their own line and record the exit code** before any push or build:

```bash
python -m unittest discover -s tests -v; echo "tests exit=$?"
```

Never chain tests and the next step with `;` (observed: a branch was pushed with a failing test because the chained command did not stop). Exit 0 = pass; non-zero = fail, stop. A runner that reports **blocked** (for example exit 2 because PowerShell 7 is not on this agent's PATH) is neither pass nor fail: write `not-run (blocked: <reason>)` and cite the CI job that ran it (template ci.yml runs Windows) as the evidence.

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
| G0 | Release lane is free: no other open release PR; no `v<version>-*` branch by another writer; the expected `main` SHA (from the handoff prompt, when one exists) still equals the remote. **When the project's rules define a "Release in progress" marker** (for example a line in quick context): read it and stop if another session holds it; write yours (`Release in progress: v<version>, <tool> session <id>, started <time>`) **before the first push** of the release branch | `gh pr list --state open`; `git ls-remote --heads origin`; `git ls-remote origin main`; read the marker file. One release in flight per repo — observed collision 2026-10-08: two agents built "v1.6.2" from different bases. Observed 2026-10-09: a release branch was pushed while the project's marker was still empty |
| G1 | Working tree clean; candidate built from the exact commit to be tagged, in a fresh clone outside synced folders (section 2); commits on the release branch authored by the owner's identity (AI only as trailer) | `git status --porcelain` empty; record `git rev-parse HEAD`; `git log --format='%an <%ae>' origin/main..HEAD` lists only the owner identity |
| G1c | (at tag time) The tag target is the **merge commit of the merged release PR** — no direct commit to `main` between merge and tag | `gh pr list --state merged --search <sha>` non-empty, or the commit message carries `(#<n>)`; `git log <sha>..origin/main` empty or explained. Observed: a final-wording commit pushed straight to `main` after the PR merge was tagged and never reviewed |
| G2 | Versions agree; no unintended stale versions | `check_versions.py` exit 0 |
| G3 | Release notes file exists and reads as released text: no candidate/"not released" status, no placeholders or empty bullets, no pre-written publish date; WARN on internal IDs (session UUIDs, tracker rows) — those go in the PR body | `check_versions.py` (notes body lint). Observed: two immutable releases whose public body still says "candidate, not released" |
| G3b | Record files are not damaged: `HOST_INSTALL_LOG.md`, `CHANGELOG.md`, `README.md`, release notes are UTF-8 without BOM, no NUL bytes, LF, one install-log header | `check_versions.py` (record lint; also in template ci.yml). Observed: a PowerShell 5.1 `>>` append wrote UTF-16 bytes into a UTF-8 index |
| G4 | Workflow is draft-first and never clobbers | `check_versions.py --workflow .github/workflows/release.yml` |
| G4b | Windows and Ubuntu builds give identical archives | CI `same-bytes` job (template ci.yml) |
| G5 | Tests run on their own line with the exit code recorded (section 2); CI green on this commit, including Windows if helpers run on Windows | `tests exit=0 (N run)`; CI run link |
| G6 | Skill validators pass (frontmatter, name matches folder, description <= 1024 chars; OpenAI skill/plugin validators pinned by commit) | CI or local run |
| G7 | Candidate built, every archive byte-verified, packaged scripts smoke-tested | builder output; no warnings left unexplained |
| G8 | Line endings: `.md`/`.py` are LF in the repository (`.gitattributes`); no CRLF in the Opal package | builder asserts Opal; `git ls-files --eol` |
| G8b | No unintended executable bits (mode drift between OSes is real: 3 files went 100755 on Linux while Windows kept 100644, folder-cleanup v1.6.1) | `git ls-files -s \| grep ^100755` lists only intended scripts |
| G8c | Tag kind matches the repository's convention — mixed lightweight/annotated tags break `v<tag>^{}` peeling and citation | `git cat-file -t v<previous>` (expect `tag` for annotated) |
| G9 | Each host package matches host-matrix.md rules for this release | compare package listing with Table A |
| G10 | Tag does not exist yet locally or remotely | `git ls-remote --tags origin vX.Y.Z` empty |
| G11 | Out-of-repo version touch points: the wiki (`<repo>.wiki.git`), marketplace listings and host store descriptions name the new version or are explicitly listed as not-run | `check_versions.py --previous X.Y.Z --extra-root ../wiki-clone`; anything unreachable gets a `not-run` line, never a silent pass |
| G12 | Visual check before a public push: README renders (tables, any diagram), links and image alt text are current, and the social-preview image is not contradicted by this release's content. Update assets only when content changed | open the rendered README on the branch; repository settings → social preview (owner) |
| G13 | One-host trial of the **exact candidate**: install one candidate archive on one host per verify-and-record.md (backup outside scanned folders, duplicate check), run the check prompt, save the reply as an evidence file. `not-run` is allowed with a reason | evidence file path; candidate archive sha256. Observed: a one-host trial found 6 defects before the tag; releases without one were superseded within hours 5 times |
| G14 | Repository copies match the skill's current templates: `packaging/check_versions.py`, `verify_release.py`, `build_packages.py`, `.github/workflows/*.yml`, `HOST_INSTALL_LOG.md` header. List stale copies; update them or record why not | `check_versions.py --drift-against <path to installed github-release skill>` |

## 4. Windows lessons (observed)

- Clone with `core.autocrlf=false`; `git am` failed with `autocrlf=true`. The template `.gitattributes` forces LF for all text so Windows and Linux builds match.
- A local candidate is only comparable to the CI build if both use the same builder version; the builder pins ZIP metadata (`create_system`) so the OS does not change the bytes. Different zlib versions could still change compressed bytes; if a candidate differs only that way, compare member contents and record it. When the owner's machine and CI run different OSes and bytes still differ, the comparable candidate is the **CI artifact of the gated commit** (download it from the CI run) rather than the laptop build.
- If `git status` reports "dubious ownership" (clones inside tool-owned dirs such as `~/.codex/...`), use `git -c safe.directory=<absolute path>` for that clone only; never set `safe.directory=*`.
- Child-process stdout is cp1252 on Windows; helpers must write UTF-8 safely.
- Do not write shared text files with Windows PowerShell 5.1 (BOM/ANSI; `>>` appends UTF-16). Preserve a BOM only where a file already needs one. Append with an explicit encoding (verify-and-record.md "Append safely").
- Do not retype large files through chat tools; copy or apply patches.

## 5. Gate report format

```text
Gate: <skill> v<version> at <commit>  —  PASS | FAIL | INCOMPLETE
Bump: minor (trigger: new gate check G13)
G1 pass  clean tree, HEAD 1a2b3c4, author <owner noreply>
G5 pass  tests exit=0 (31 run); CI run <link>
G13 not-run  no host available in this session; owner to trial <archive>
...
Candidate: <folder>, SHA256SUMS sha256 <first 12>
```

INCOMPLETE is not PASS. Do not propose a tag on INCOMPLETE.
