# Host matrix — which package each host gets

Dated rules for building and choosing packages. Other skills (for example ai-prompting) should link here instead of copying. Re-verify a rule before relying on it for a release; hosts change without notice.

Source types: **observed** (an upload or import by the owner or an agent, with date), **official-doc** (URL + date read), **repo** (documented in a skill repository, not re-tested here), **inferred**.

## Table A — package rules

Reference: `multi-agent-folder-cleanup` v1.6.1. On 2026-10-08 the author rebuilt its seven published ZIPs from tag v1.6.1 with `templates/build_packages.py` and a `packages.json` describing them; every SHA-256 matched the digest GitHub lists for the v1.6.1 assets. Anyone can repeat this check.

| Package suffix | Hosts | Include / transform | Omit | Source | Checked |
|---|---|---|---|---|---|
| `-UNIVERSAL-skill` | Claude app skill upload; ChatGPT/Codex standalone skills; Antigravity; local models; any skills folder | skill folder + `LICENSE.txt` + `INSTALL.md`, folder entries | — | repo (folder-cleanup install guide) | 2026-10-06 |
| `-claude-code-plugin` | Claude Code `/plugin install` only | `.claude-plugin/*.json` + `skills/<name>/…` + README, CHANGELOG, LICENSE, INSTALL | — | repo; the Claude app uploader rejects plugin files (repo) | 2026-10-06 |
| `-codex-chatgpt-plugin` | Codex / ChatGPT plugin | `.codex-plugin/*.json` + `skills/<name>/…` + README, CHANGELOG, LICENSE, INSTALL | — | repo; OpenAI validators pinned in CI | 2026-10-06 |
| `-microsoft-copilot-agent-only` | Microsoft Copilot agent upload; **Grok** | universal minus PowerShell | `*.ps1` | Copilot: repo (validator rejects `.ps1`). Grok: observed 2026-10-05 in an owner upload test (Universal rejected for `.ps1`, this ZIP accepted) — documented as | 2026-10-08 |
| `-gemini-apps-only` | Gemini Apps upload | skill minus listed omissions | `*.ps1`, `*.yaml`, `*.yml` (precaution, untested), `agents/`, nested `references/*/`, scripts the security scan rejects (folder-cleanup: `audit_folder.py`, credential-hint read guards) | observed: 1.4.1 rejection of `audit_folder.py` (repo CHANGELOG); 1.6.1 package **accepted**, owner-reported 2026-10-08 — it contains a `ctypes`/kernel32 script, so ctypes alone is not rejected (if that was the published asset) | 2026-10-08 |
| `-opal-only` | Opal import | `SKILL.md` with only `name` + `description` frontmatter; top-level `references/*.md`; LF endings; **no folder entries** | everything else | observed: confirmed by import (repo CHANGELOG 1.5.0); per-file size rejection above ~48–79 KB observed 2026-10-03, approximate | 2026-10-06 |
| `-project-rules-optional` | add-on, any host | only if the skill ships optional add-on material | — | repo | 2026-10-06 |

## Install channels per host

A host can have several install channels that drift to different versions independently (observed on Codex three times: standalone dir vs Personal Plugin at different versions; the standalone dir vanished twice between turns). Rules: record the **Channel** in every install-log row; a version check reads the **installed files** (`SKILL.md` metadata, helper `--version`), never a catalog cache — if a cache is cited, record its mtime.

| Host | Channels |
|---|---|
| Claude | app skill upload (Settings → Capabilities → Skills); Claude Code plugin (`/plugin install` or marketplace) |
| Codex / ChatGPT | standalone skills dir (`~/.codex/skills/`); Personal Plugin (manual "Upload new version" in the ChatGPT UI — no API); desktop marketplace (cache `~/.codex/cache/remote_plugin_catalog/*.json` is stale evidence) |
| Antigravity | `~/.gemini/config/skills/` from the repository |
| Gemini Apps, Copilot, Grok, Opal | single upload channel each (UI) |

## Host notes

- **Claude app**: upload the Universal ZIP under Settings → Capabilities → Skills (repo-documented path).
- **Claude Code**: plugin ZIP or the repository marketplace (`.claude-plugin/marketplace.json`).
- **Codex / ChatGPT**: plugin via Plugin Creator; standalone skill via the Universal ZIP.
- **Microsoft Copilot**: two distinct surfaces — **Agent Builder** (Configure → Skills, takes the agent ZIP) and **chat attachment** (observed 2026-10-07 rejecting the ZIP but accepting Markdown files attached directly). The documented Agent Builder layout is root-level `SKILL.md`, while this package nests it under `<name>/`; whether Agent Builder requires the root layout is an **open question** (pending test, ai-prompting W-015) — do not change the package until that test runs. The sandbox has no direct network; packaged scripts must not need it (repo).
- **Grok**: sandbox is POSIX; OneDrive/SharePoint hydration cannot be checked there (repo).
- **Gemini Apps**: the skill uploader rejects a folder containing a file without an extension ("The skill folder contains a file with an unsupported file type", observed 2026-10-08 on `templates/gitattributes`); the same package without that file was accepted, including `.py`, `.json`, `.md` and `.txt`. Whether packaged `.py` scripts can run there is untested. Never rename or obfuscate code to pass the scan; omit and document. Add-on files must keep an extension (`LICENSE.txt`, not `LICENSE`).
- **Opal**: references must be flat for the skill to work there; keep essential instructions in `SKILL.md` and top-level `references/`.
- **Antigravity**: installs from the GitHub repository (repo-documented; untested here).
- **Local models (Ollama, LM Studio, llama.cpp front-ends)**: point the system prompt or context loader at `SKILL.md`.
- **Manus**: not in v1; no package rules recorded.
- **Sandboxed review hosts (Opal, Manus, Copilot)**: review-only for releases — never do git work there. Observed: an Opal workspace reset wiped a clone before it could push (2026-10-07).

## Open questions

- Does Gemini accept `.yml` templates? (github-release omits them as a precaution; `.py`/`.json`/`.md`/`.txt` were accepted 2026-10-08.)
- Can packaged `.py` scripts execute inside Gemini Apps?
- Is the Opal size limit per file or per package, and what is the exact threshold?
- Which hosts load an `AGENTS.md` from a project folder? Not a packaging rule; tracked in the project.
- Does Copilot Agent Builder require root-level `SKILL.md` in the ZIP? (See Microsoft Copilot host note; pending W-015 test.)
