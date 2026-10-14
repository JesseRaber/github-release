# Set up a skill repository

Use in **Setup**. Draft everything locally first; creating the GitHub repository, pushing and changing settings are separate owner approvals.

## Layout

```text
<repo>/
  skills/<name>/SKILL.md, references/, scripts/, agents/ (optional)
  packaging/build_packages.py      from templates/
  packaging/packages.json          from templates/
  packaging/version_files.json     from templates/
  packaging/check_versions.py      copy of this skill's scripts/check_versions.py
  packaging/verify_release.py      copy of this skill's scripts/verify_release.py
  packaging/INSTALL-*.md           which-ZIP guide per audience
  packaging/RELEASE_NOTES_vX.Y.Z.md
  .claude-plugin/plugin.json, marketplace.json   (if Claude Code plugin is built)
  .codex-plugin/plugin.json                      (if Codex plugin is built)
  .github/workflows/ci.yml, release.yml          from templates/
  .gitattributes                                 from templates/gitattributes
  HOST_INSTALL_LOG.md                            from templates/
  tests/
  README.md  CHANGELOG.md  LICENSE
```

## Defaults

- Commit identity: in every clone, `git config user.name`/`user.email` = the owner's name and GitHub noreply address before the first commit. AI help is credited only in a `Co-Authored-By:` trailer, never as the author (release-gate.md section 2).
- License: MIT unless the owner says otherwise.
- `.gitattributes`: LF for `.md`, `.py`, `.json`, `.yml`; leave `.ps1` as the repository already has it.
- External validators downloaded at pinned commits.
- Branch protection on `main`: PR required, CI required.
- "Automatically delete head branches" ON (settings change, approval) — stale merged branches otherwise accumulate (9 observed on one repo before a manual tidy).
- Social-preview image (Settings → General, 1280×640) and repository Website field set before wide sharing; both are owner settings actions.
- Releases: enable **immutable releases** in repository settings (owner approval; it is a settings change).
- CI on Ubuntu, and on Windows when helpers are meant to run on Windows; the template also runs on pushed `release/**` and `v*` branches and on `workflow_dispatch`, so a candidate branch has CI before its PR exists.
- Actions pinned by full commit SHA with the release tag in a trailing comment (`# v7.0.1`); bump the pins when an action's runtime is deprecated, and resolve the SHA from the tag yourself (`git ls-remote https://github.com/actions/<name> refs/tags/<tag>`).
- README opens with a "which ZIP do I download?" table generated from host-matrix.md.

## Approval order

1. Owner reviews the local draft repository.
2. Create the repository (approval: name, visibility, owner account).
3. Push `main` (approval).
4. Settings: branch protection, immutable releases (approval). Settings changes are usually refused from cloud agent sessions (observed 2026-10-08) and run in the owner's browser or signed-in `gh`; GitHub may demand the owner's passkey ("sudo mode") — stop and ask the owner to complete it, then confirm the result by API read (for example `gh api repos/<owner>/<repo>/branches/main/protection`).
5. First release follows publish.md.
