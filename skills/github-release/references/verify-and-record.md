# Verify published assets and record host installs

## Verify

`scripts/verify_release.py` checks, without network:

| Check | Fails when |
|---|---|
| Checksums | a file differs from `SHA256SUMS.txt`, or a listed file is missing, or an unlisted ZIP is present |
| Naming | an archive name does not contain `-<version>-` |
| Download count (`--release-json`) | printed first: `downloaded N of M listed assets`; N < M fails (a download problem, not a release defect) |
| GitHub metadata (`--release-json`) | an asset's `digest` differs from the local file, or GitHub lists an asset not downloaded; reports `draft` / `immutable` |
| Author and title (`--release-json`) | the release was not created by `github-actions[bot]` (override with `--expected-author`), or its title does not end with ` v<version>` |
| Notes body (`--notes FILE`) | the release body differs from the notes file, except for one appended `## Known issues (added YYYY-MM-DD)` section (publish.md section 5) |
| Release state (`--expect-published`, `--expect-immutable`) | after publishing: the release is still a draft, or not immutable. Pass `--expect-immutable` whenever the repository setting is ON (publish approval block); the record says ON or OFF |
| Candidate (`--candidate`) | a published archive is not byte-identical to the local candidate with the same name |
| ZIP integrity | `testzip` fails or members are duplicated |

Exit 0 only when every requested check ran and passed. Quote its output in the report; "verified" without that output, or an equivalent described check, must say "not verified".

Spot-check content too: open one packaged `SKILL.md` per host package and confirm the version line.

## Install procedure (replacing an existing host copy)

Where hosts actually load from (observed; record the path in T2 of the check prompt):

- **Claude Code with a directory marketplace** loads `SKILL.md` from the marketplace **source folder**, not from the plugin cache. Keep that source in a stable folder outside synced storage (for example `%USERPROFILE%\.claude\local-marketplaces\<name>`), and update it there.
- **Never judge an install's age by file mtime.** ZIP extraction sets the archive's fixed timestamps (the builder pins them), so a fresh install can look years old. Use hashes and the version line.

1. **Back up outside every scanned folder.** Hosts search every subfolder of their skills folder for `SKILL.md` (Codex observed 2026-10-09), so a backup kept anywhere inside it loads as a second skill with the same name and can shadow the new install. Put the backup **beside** the skills folder, never inside it — for example `~/.codex/skill-backups/<name>.pre-v<new>-<stamp>` next to `~/.codex/skills/`, or `~/.gemini/config/skills_backups/` next to Antigravity's `skills/`. This applies to every host: Codex, Antigravity, Claude Code (including marketplace source dirs and plugin caches) and any other. If a backup must stay inside a scanned folder, rename its `SKILL.md` to a non-loading name such as `SKILL.backup-not-loaded.md` before the install, and record the rename. The same rule covers staging and extraction folders.
2. Write a SHA-256 manifest of the backup and `sha256sum -c` it before touching the installed copy.
3. Verify the new archive against the release `SHA256SUMS.txt`.
4. Replace, then compare the installed tree to the archive **file for file, including the count of extra files (must be 0)** — a hash-match of present files does not catch leftovers from the old version.
5. **Duplicate-name check (required).** List every `SKILL.md` under all of that host's skill folders, searching all subfolders, and read each one's `name:` line:

   ```text
   python scripts/check_skill_duplicates.py <host skills folder> [<more>] --name <skill> --expect-version <new>
   ```

   Exactly one `SKILL.md` may carry the installed skill's name, and it must report the new version. More than one is a **failed install**: report every path, move or rename the extra copies per step 1, and rerun before calling the install done. Run it on every folder the host scans (see host-matrix.md "Install channels per host").
6. Tell the owner to **restart the host** (quit and reopen the app or CLI) so it reloads its skill list.
7. After the restart, confirm the loaded report line and its path inside the host (`templates/HOST_INSTALL_CHECK_PROMPT.md` generates the read-only check to paste into the host). The path in the line exposes shadow copies in backups, plugin caches and stale channels.

**What each check proves.** Byte-matching files (step 4), a correct helper `--version` and a clean duplicate check (step 5) prove the files on disk are right. They do not prove the host loads them: on 2026-10-09 all 22 files of a Codex install matched the release and the helpers reported the new version, yet Codex still loaded the old copy from a backup inside `.codex/skills`. Only a check inside the host — its skill view, its "reveal in folder" target, or the skill's arrival line with its path — confirms the load.

**Candidate trials count once the bytes match.** A trial install of a release candidate (gate G13) counts as the host install of the published version when the installed archive's SHA-256 equals the published asset's. Write the row with Action `install (trial)` and Evidence `candidate <first 12> = published asset <first 12>`; no reinstall is needed. If the hashes differ, the trial is evidence about the candidate only, and the host needs the published archive.

## Save host replies as evidence files

Before writing a row, save the host's reply **verbatim** (the check-prompt report, an error message, a screenshot) as a file in the project's records — for example `Evidence/<date>_<host>_<skill>-v<version>_check.md`, with a header line naming who pasted it and when. The row's Evidence field cites that path. Observed: host replies that existed only as pasted chat text were lost when the chats were deleted, leaving rows with no evidence behind them.

## Record host installs

Each skill repository keeps `HOST_INSTALL_LOG.md` (template in `templates/`). Append one row per attempt; never edit old rows except to add a `superseded` row that points forward.

| Field | Rule |
|---|---|
| Date | ISO date and time with timezone, when known |
| Version / Asset | exact archive name; first 12 of its SHA-256 |
| Host / account | e.g. Gemini Apps, personal; Copilot, tenant name |
| Channel | which install channel on that host (see host-matrix.md "Install channels per host") |
| Action | upload, update, remove, smoke-test |
| Result | `accepted`, `rejected`, `accepted-not-loaded`, `loaded-smoke-pass`, `loaded-smoke-fail`, `superseded` |
| Displayed | the name/version the host shows, or `none shown` |
| Evidence | `observed` (agent saw it), `user-reported`, screenshot/error-text path |
| Host load | `confirmed in host` only after a check inside the host after restart (skill view, "reveal in folder", or arrival line with path) showed the new version from the installed path; otherwise `files verified; host load not checked`. A failed duplicate check is `failed: duplicate name` |

Rules:

- **Append safely.** Write rows with an explicit UTF-8 method and read the last line back:

  ```python
  with open('HOST_INSTALL_LOG.md', 'a', encoding='utf-8', newline='\n') as f:
      f.write(row.rstrip('\n') + '\n')
  print(open('HOST_INSTALL_LOG.md', encoding='utf-8').read().splitlines()[-1])
  ```

  On Windows without Python: `[IO.File]::AppendAllText($path, $row + "`n", [Text.UTF8Encoding]::new($false))`. Never `>>`, `Add-Content` or `Out-File` in Windows PowerShell 5.1 (observed: a `>>` append wrote UTF-16 bytes into a UTF-8 file), and never rewrite the whole file to add a row. `check_versions.py` lints record files for BOM, NUL bytes and CRLF.
- "It installed fine" from the owner is a valid row with `Evidence: user-reported`. Ask once which archive (or hash) was uploaded; if unknown, write `asset: unknown`.
- A rejection row quotes the host's error text. Rejections update Table A in host-matrix.md (new dated rule) only after the cause is isolated, for example by removing one file at a time in a local, unpublished test copy.
- Do not delete a test install until its row is written.
- Never write `loaded`, `loaded-smoke-pass` or `host loads new version` from file hashes, helper `--version` output or a duplicate check alone; those rows say `files verified; host load not checked` until the in-host check is done.
- A release does not change any host. Never mark a host updated because a release was published.
