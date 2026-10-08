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

- License: MIT unless the owner says otherwise.
- `.gitattributes`: LF for `.md`, `.py`, `.json`, `.yml`; leave `.ps1` as the repository already has it.
- Actions pinned by full commit SHA; external validators downloaded at pinned commits.
- Branch protection on `main`: PR required, CI required.
- Releases: enable **immutable releases** in repository settings (owner approval; it is a settings change).
- CI on Ubuntu, and on Windows when helpers are meant to run on Windows.
- README opens with a "which ZIP do I download?" table generated from host-matrix.md.

## Approval order

1. Owner reviews the local draft repository.
2. Create the repository (approval: name, visibility, owner account).
3. Push `main` (approval).
4. Settings: branch protection, immutable releases (approval).
5. First release follows publish.md.
