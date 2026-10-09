# Verify published assets and record host installs

## Verify

`scripts/verify_release.py` checks, without network:

| Check | Fails when |
|---|---|
| Checksums | a file differs from `SHA256SUMS.txt`, or a listed file is missing, or an unlisted ZIP is present |
| Naming | an archive name does not contain `-<version>-` |
| GitHub metadata (`--release-json`) | an asset's `digest` differs from the local file, or GitHub lists an asset not downloaded; reports `draft` / `immutable` |
| Release state (`--expect-published`, `--expect-immutable`) | after publishing: the release is still a draft, or not immutable |
| Candidate (`--candidate`) | a published archive is not byte-identical to the local candidate with the same name |
| ZIP integrity | `testzip` fails or members are duplicated |

Exit 0 only when every requested check ran and passed. Quote its output in the report; "verified" without that output, or an equivalent described check, must say "not verified".

Spot-check content too: open one packaged `SKILL.md` per host package and confirm the version line.

## Install procedure (replacing an existing host copy)

1. Back up the currently installed copy with a SHA-256 manifest and `sha256sum -c` the backup before touching anything.
2. Verify the new archive against the release `SHA256SUMS.txt`.
3. Replace, then compare the installed tree to the archive **file for file, including the count of extra files (must be 0)** — a hash-match of present files does not catch leftovers from the old version.
4. Confirm the loaded report line and its path in a fresh host session (`templates/HOST_INSTALL_CHECK_PROMPT.md` generates the read-only check to paste into the host); the path in the line is what exposes shadow copies in plugin caches and stale channels.

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

Rules:

- "It installed fine" from the owner is a valid row with `Evidence: user-reported`. Ask once which archive (or hash) was uploaded; if unknown, write `asset: unknown`.
- A rejection row quotes the host's error text. Rejections update Table A in host-matrix.md (new dated rule) only after the cause is isolated, for example by removing one file at a time in a local, unpublished test copy.
- Do not delete a test install until its row is written.
- A release does not change any host. Never mark a host updated because a release was published.
