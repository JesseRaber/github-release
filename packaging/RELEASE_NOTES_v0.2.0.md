# github-release 0.2.0

Hardening release from real multi-agent release history: a release-lane gate (one release in flight, expected-SHA refusal), connector byte-drift checks, fresh-clone and sandbox rules, per-host install channels with an install-check prompt template, an install procedure with backups and zero-extra-file verification, out-of-repo version checks (`--extra-root`), and a loaded line that names its own path. See CHANGELOG.md for the full list.

Verify downloads with `sha256sum -c SHA256SUMS.txt`.

## Publication boundary

Installed host copies are updated separately; this release does not change any host by itself.

---
Built by [Jesse Raber](https://jesseraber.net) · [YouTube](https://www.youtube.com/@Jesse_Raber)
