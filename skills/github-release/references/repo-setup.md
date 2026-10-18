# Set up a skill repository

Use in **Setup**. Draft everything locally first; reuse or obtain one [scope bundle](approval-scope.md) explicitly naming repository creation, pushing and any intended settings. Settings/security changes retain mandatory action-time confirmations.

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
- Distribution and license: follow [distribution-policy.md](distribution-policy.md); record the owner-approved private/public audience and intended rights before selecting terms. Do not default to MIT or infer public intent.
- `.gitattributes`: LF for `.md`, `.py`, `.json`, `.yml`; leave `.ps1` as the repository already has it.
- External validators downloaded at pinned commits.
- Branch protection on `main`: PR required, CI required.
- "Automatically delete head branches" ON (settings change, approval) — stale merged branches otherwise accumulate (9 observed on one repo before a manual tidy).
- Public projects only: accurate relevant topics/keywords, useful docs/examples, attribution, and owner-approved website/storefront links; social-preview and repository Website settings need explicit scope coverage and any mandatory host confirmation. No promotion/storefront content for private projects. See [distribution-policy.md](distribution-policy.md).
- Releases: enable **immutable releases** in repository settings (owner approval; it is a settings change).
- CI on Ubuntu, and on Windows when helpers are meant to run on Windows; the template also runs on pushed `release/**` and `v*` branches and on `workflow_dispatch`, so a candidate branch has CI before its PR exists.
- Actions pinned by full commit SHA with the release tag in a trailing comment (`# v7.0.1`); bump the pins when an action's runtime is deprecated, and resolve the SHA from the tag yourself (`git ls-remote https://github.com/actions/<name> refs/tags/<tag>`).
- README opens with a "which ZIP do I download?" table generated from host-matrix.md.

## Repository transport and mode checks

When copying files from a device or bridge into a Git clone, do not use `cp -a` for source files: preserved device modes can turn ordinary files into `100755`. Restore affected files from the base tree, apply the intended content change, and inspect `git diff --summary` for unintended mode changes before committing. A shallow clone may lack a local tracking ref even after a successful push; compare the remote ref and expected commit directly before calling a stop-hook report of "unpushed" a failure. Neither observation substitutes for checking the remote result.

If `gh pr create` fails because its GraphQL request is blocked, create the PR through the GitHub REST pulls endpoint (`gh api -X POST repos/<owner>/<repo>/pulls`) with the same reviewed title, body, head and base, then read back the PR. Keep push and PR actions within their explicit recorded scope; do not request a new approval merely for changing transport after an ordinary technical failure. Never bypass an authorization refusal.

## Execution order under the recorded scope

1. Owner reviews the concrete local draft and approves any missing scope as one bundle; reuse existing sufficient approval.
2. Create the repository (approval: name, visibility, owner account).
3. Push `main` only if the recorded scope includes that destination and automation effects; no repeat prompt for an unchanged included step.
4. Settings: branch protection, immutable releases (approval). Settings changes are usually refused from cloud agent sessions (observed 2026-10-08) and run in the owner's browser or signed-in `gh`; GitHub may demand the owner's passkey ("sudo mode") — stop and ask the owner to complete it, then confirm the result by API read (for example `gh api repos/<owner>/<repo>/branches/main/protection`).
5. First release follows publish.md.
