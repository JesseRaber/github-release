# Build host packages

## The builder

Copy `templates/build_packages.py` to `packaging/build_packages.py` and `templates/packages.json` to `packaging/packages.json` in the skill repository. The builder has its own version lifecycle (`build_packages --version`), independent of the skill and version-coupled helpers. Do not force the builder version to equal the skill version. The builder:

- reads the skill from `skills/<name>/`, version from `SKILL.md` `metadata.version`, and refuses if plugin manifests disagree;
- builds each archive in `packages.json` with a fixed timestamp, sorted members and fixed permissions, so the same source gives the same bytes;
- re-reads every archive, byte-compares every member, asserts no omitted file slipped in, compiles every packaged Python script and runs `--version` on the scripts listed in `smoke_version_scripts`;
- writes `SHA256SUMS.txt` and `BUILD_EVIDENCE.json`; never tags, uploads or installs.

Historical fidelity check (2026-10-08, by the author, with the then-current builder; newer ZIP file-type metadata changes archive bytes): with a `packages.json` describing multi-agent-folder-cleanup's seven packages (six like `templates/packages.json` plus a `subtree` add-on), this builder reproduced all seven published v1.6.1 ZIPs byte-for-byte against GitHub's asset digests.

Independent of `packages.json`, the builder also refuses `.ps1` in Copilot packages, `.ps1`/`.yml`/`.yaml` and files without an extension (e.g. `gitattributes`, `LICENSE`) in Gemini packages and non-Markdown in Opal packages, and fails if a script named in `smoke_version_scripts` is never packaged.

## packages.json

```json
{
  "skill": "my-skill",
  "smoke_version_scripts": ["my_helper.py"],
  "packages": {
    "UNIVERSAL-skill": {"layout": "skill", "add": {"LICENSE.txt": "LICENSE", "INSTALL.md": "packaging/INSTALL-universal.md"}},
    "gemini-apps-only": {"layout": "skill", "exclude_suffix": [".ps1", ".yaml", ".yml"], "exclude_no_suffix": true, "exclude_prefix": ["agents/"]}
  }
}
```

| Key | Meaning |
|---|---|
| `layout` | `skill` (folder `<name>/…`), `plugin` (`<name>/skills/<name>/…` + `metadata` manifests), `opal` (flat Markdown, no folder entries), `subtree` (`from` → `to`, for add-ons) |
| `exclude_prefix` / `exclude_suffix` / `exclude_files` | paths relative to the skill folder to leave out |
| `exclude_no_suffix` | `true` leaves out skill files whose name has no extension (required for Gemini Apps) |
| `add` | extra files: archive path inside `<name>/` → repository path |
| `metadata` | plugin manifest folder (`.claude-plugin`, `.codex-plugin`) |
| `folder_entries` | override; default true except `opal` |
| `extra_packages` (top level) | names of packages beyond the six known ones (e.g. a `subtree` add-on); unknown names fail the build so host invariants cannot be bypassed by renaming |

Start from the six packages in `templates/packages.json` and remove hosts the skill does not target. Every omission needs a reason in host-matrix.md.

## Input and validation boundaries

- Every repository source and metadata read refuses linked ancestors, Windows reparse points and paths outside the repository. Archive targets refuse absolute paths, drive prefixes, backslashes and traversal segments.
- ZIP regular files carry POSIX type and permission mode `0100644`. Helpers run through Python; this does not promise executable script permissions.
- Exclusions and host invariants treat suffixes case-insensitively. Dotfiles without a suffix count as extensionless; host acceptance still requires a real upload check.
- Frontmatter delimiters occupy their own lines. The standard-library builder requires an unquoted single-line name and `metadata.version` as a quoted semantic version. Opal name and description must occupy single lines; all multiline forms are refused rather than truncated. Keep only its supported name/description keys.
- All packaged Python files, including templates, compile. Identical bytes are compiled once per invocation; version smoke checks run only for configured helpers and reuse identical helper bytes.
- Distributable helper/template copies stay standalone. Keep repository copies byte-identical to them and run the drift check; do not introduce imports that require an installed skill.

## Rules

- One builder for local candidates and the release workflow; never hand-zip a release asset.
- Name archives by audience: `<name>-<version>-<suffix>.zip`.
- Keep `.md` and `.py` LF in the repository (`templates/gitattributes`); the Opal package asserts no CR.
- If a build normalizes bytes (CRLF to LF), the evidence must say so; never claim byte-identical across a normalization.
- A host-specific omission is never a disguise. Do not rename, encode or split code to pass a scan.
- Skills whose instructions rely on nested references or templates must still work from `SKILL.md` + top-level references, or the Opal/Gemini packages will silently lose behavior. Say in `SKILL.md` what is missing on those hosts.
