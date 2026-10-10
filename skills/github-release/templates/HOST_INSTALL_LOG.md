# Host install log — SKILL-NAME

Append-only. One row per attempt. Never edit an old row; add a `superseded` row instead.
Evidence: `observed` (agent saw it), `user-reported`, or a path to a screenshot / error text.
Host load: `confirmed in host` only after an in-host check after restart (skill view, "reveal in folder", arrival line with path); otherwise `files verified; host load not checked`. Matching bytes and `--version` prove the files, not the load.

| Date (TZ) | Version | Asset (sha256 first 12) | Host / account | Channel | Action | Result | Displayed | Evidence | Host load | By |
|---|---|---|---|---|---|---|---|---|---|---|
