# github-release 0.3.0

Minor release. It turns lessons from a real skill's release history into gate checks and helper output, and fixes install backups that could shadow a new install.

## Changes

**Installs**

- Backups can no longer shadow a new install. Backups go beside a host's skills folder, never inside it. A required duplicate-name check runs after every install, using the new helper `check_skill_duplicates.py`. The install log gains a `Host load` column: `confirmed in host` only after a check inside the restarted host.
- A trial install of the release archive counts as the host install when its hash equals the published asset.
- Host replies are saved word for word as evidence files. Install-log rows are appended with an explicit UTF-8 write and read back.

**Gate and helpers**

- `check_versions.py` lints the release notes. It fails on leftover status wording that says the release is unfinished, on placeholders, empty bullets and publish dates written ahead of time. It warns on internal IDs. The release workflow runs it before it creates the draft.
- `check_versions.py` also lints record files (install log, changelog, README, notes): UTF-8 without BOM, no NUL bytes, LF line endings.
- `check_versions.py --drift-against` (given the skill folder) lists repository copies of helpers and workflows that no longer match the skill.
- `verify_release.py` reports `downloaded N of M listed assets` first. It fails a release not created by the workflow or with the wrong title. `--notes` compares the release body with the notes file; the only allowed later edit is an appended, dated "Known issues" section.
- New gate rules: a patch/minor/major bump table; the project's "release in progress" marker is written before the first push; release commits use the owner's identity; the tag goes only on the release PR's merge commit; the test exit code is recorded on its own line; a one-host trial of the exact release archive; a template drift check.

**Publishing**

- Every publish approval states whether immutable releases are on, and asks once when they are off.
- Merge, tag push, publish, branch delete and settings are expected to be refused from cloud agent sessions. The skill hands the owner one combined command block.
- Asset downloads follow the release's own asset list and check the count. Releases created by hand are not allowed.

**Hosts and CI**

- Gemini: regular Gemini chat rejects skills that contain scripts; Gemini Spark loads them. The Gemini package targets Spark.
- Install channels and expected load paths are documented for Claude app, ChatGPT web, Grok and Microsoft Copilot. The install check falls back to the loaded line where a host hides the frontmatter, and counts a helper version only from output it shows.
- The CI template also runs on pushed release branches and on manual dispatch. GitHub Actions are pinned to current major versions by commit SHA.

## Packages

| Archive | For |
|---|---|
| `github-release-0.3.0-UNIVERSAL-skill.zip` | Claude app upload, ChatGPT/Codex standalone skills, Antigravity, local models, any skills folder |
| `github-release-0.3.0-claude-code-plugin.zip` | Claude Code `/plugin install` |
| `github-release-0.3.0-codex-chatgpt-plugin.zip` | Codex / ChatGPT plugin |
| `github-release-0.3.0-microsoft-copilot-agent-only.zip` | Microsoft Copilot agent upload, Grok |
| `github-release-0.3.0-gemini-apps-only.zip` | Gemini Spark (regular Gemini chat rejects skills with scripts) |
| `github-release-0.3.0-opal-only.zip` | Opal import |

Verify downloads with `sha256sum -c SHA256SUMS.txt`.

## Publication boundary

Installed host copies are updated separately; this release does not change any host by itself.

---
Built by [Jesse Raber](https://jesseraber.net) · [YouTube](https://www.youtube.com/@Jesse_Raber)
