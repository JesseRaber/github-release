# Build host packages

## The builder

Copy `templates/build_packages.py` to `packaging/build_packages.py` and `templates/packages.json` to `packaging/packages.json` in the skill repository. The builder:

- reads the skill from `skills/<name>/`, version from `SKILL.md` `metadata.version`, and refuses if plugin manifests disagree;
- builds each archive in `packages.json` with a fixed timestamp, sorted members and fixed permissions, so the same source gives the same bytes;
- re-reads every archive, byte-compares every member, asserts no omitted file slipped in, compiles every packaged Python script and runs `--version` on the scripts listed in `smoke_version_scripts`;
- writes `SHA256SUMS.txt` and `BUILD_EVIDENCE.json`; never tags, uploads or installs.

Fidelity check (2026-10-08, by the author, repeatable): with a `packages.json` describing multi-agent-folder-cleanup's seven packages (six like `templates/packages.json` plus a `subtree` add-on), this builder reproduced all seven published v1.6.1 ZIPs byte-for-byte against GitHub's asset digests.

Independent of `packages.json`, the builder also refuses `.ps1` in Copilot packages, `.ps1`/`.yml`/`.yaml` in Gemini packages and non-Markdown in Opal packages, and fails if a script named in `smoke_version_scripts` is never packaged.

## packages.json

```json
{
  "skill": "my-skill",
  "smoke_version_scripts": ["my_helper.py"],
  "packages": {
    "UNIVERSAL-skill": {"layout": "skill", "add": {"LICENSE.txt": "LICENSE", "INSTALL.md": "packaging/INSTALL-universal.md"}},
    "gemini-apps-only": {"layout": "skill", "exclude_suffix": [".ps1", ".yaml", ".yml"], "exclude_prefix": ["agents/"]}
  }
}
```

| Key | Meaning |
|---|---|
| `layout` | `skill` (folder `<name>/…`), `plugin` (`<name>/skills/<name>/…` + `metadata` manifests), `opal` (flat Markdown, no folder entries), `subtree` (`from` → `to`, for add-ons) |
| `exclude_prefix` / `exclude_suffix` / `exclude_files` | paths relative to the skill folder to leave out |
| `add` | extra files: archive path inside `<name>/` → repository path |
| `metadata` | plugin manifest folder (`.claude-plugin`, `.codex-plugin`) |
| `folder_entries` | override; default true except `opal` |
| `extra_packages` (top level) | names of packages beyond the six known ones (e.g. a `subtree` add-on); unknown names fail the build so host invariants cannot be bypassed by renaming |

Start from the six packages in `templates/packages.json` and remove hosts the skill does not target. Every omission needs a reason in host-matrix.md.

## Rules

- One builder for local candidates and the release workflow; never hand-zip a release asset.
- Name archives by audience: `<name>-<version>-<suffix>.zip`.
- Keep `.md` and `.py` LF in the repository (`templates/gitattributes`); the Opal package asserts no CR.
- If a build normalizes bytes (CRLF to LF), the evidence must say so; never claim byte-identical across a normalization.
- A host-specific omission is never a disguise. Do not rename, encode or split code to pass a scan.
- Skills whose instructions rely on nested references or templates must still work from `SKILL.md` + top-level references, or the Opal/Gemini packages will silently lose behavior. Say in `SKILL.md` what is missing on those hosts.
