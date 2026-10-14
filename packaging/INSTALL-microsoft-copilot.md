# Install in a Microsoft Copilot agent (also Grok)

Upload the complete `-microsoft-copilot-agent-only.zip` through the agent's Skills interface. Grok accepts the same archive (owner upload test 2026-10-05, recorded for multi-agent-folder-cleanup).

This package has no PowerShell files. The Python helpers need only the standard library and no network; Copilot's sandbox has no direct network access.

A successful upload proves only package acceptance. Test with a read-only request such as "Is this repository ready to tag?".

Expected loaded version: **GitHub Release v0.3.0**.
