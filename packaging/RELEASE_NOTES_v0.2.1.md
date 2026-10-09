# github-release 0.2.1

Patch: the Gemini Apps package no longer contains files without an extension. Gemini's skill uploader rejected 0.2.0 with "The skill folder contains a file with an unsupported file type" (`templates/gitattributes`). The builder now refuses extensionless files in Gemini packages regardless of `packages.json`. Other packages are unchanged apart from the version number.

Verify downloads with `sha256sum -c SHA256SUMS.txt`.

## Publication boundary

Installed host copies are updated separately; this release does not change any host by itself.

---
Built by [Jesse Raber](https://jesseraber.net) · [YouTube](https://www.youtube.com/@Jesse_Raber)
