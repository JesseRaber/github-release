# Tag and publish (draft first)

Use in **Publish**. Every step that changes GitHub needs the owner's explicit approval for that step. The release workflow template (`templates/release.yml`) builds on a pushed tag, creates a **draft** release, and refuses if a release for the tag already exists.

## 1. Approval block

Before any push, show this and wait for an explicit yes:

```text
APPROVAL NEEDED — tag and draft release
Repository:   <owner>/<repo>
Commit:       <full sha>  (<branch>, CI run <link>: green)
Tag:          v<version>  (annotated, on the commit above)
Gate:         PASS  (<gate report path>)
Candidate:    <folder>  SHA256SUMS <first 12>
Workflow:     builds packages, creates DRAFT release with <N> assets; nothing public yet
Not included: publishing the draft, repository settings, host installs
```

An approval covers only what the block lists.

## 2. Where release actions run

Observed 2026-10-08 (multi-agent-folder-cleanup v1.6.2 pilot): a cloud agent session could not create tags (git push dropped by the proxy; REST tag create 403), could not publish a draft (403 "editing releases not permitted"), and could not change repository settings. Expect the same split and say so before starting:

| Action | Cloud agent session | Owner's machine |
|---|---|---|
| Build candidate, gate, open/merge PRs, read releases | usually works | works |
| Push the tag | may be refused (observed) | signed-in `git` in a fresh temp clone, `core.autocrlf=false` |
| Publish the draft (`gh release edit --draft=false`) | may be refused (observed) | signed-in `gh` |
| Repository settings (branch protection, immutable releases) | refused (observed) | owner's browser or `gh`; may require the owner's **passkey ("sudo mode")** — the agent must stop and ask the owner to complete it; never ask for the credential |

When a step is refused from the cloud, do not retry through another route; hand the owner the exact command and wait. The refusal changes where the step runs, never the approval for it.

- Typical flow: feature PR (CI green) → merge → release PR with version bump (CI green) → merge → annotated tag on the merge commit.

```bash
git tag -a v1.2.0 -m "<skill> v1.2.0" <merge-commit-sha>
git push origin v1.2.0
```

## 3. Draft created → verify

1. Wait for the workflow. Confirm the release is a **draft** (`gh release view v1.2.0 --json isDraft`).
2. Download every asset: `gh release download v1.2.0 --dir ../draft-1.2.0` (drafts need an authenticated `gh`). `gh release download` uses GraphQL, which some proxies block (observed); fall back to REST per asset:

   ```bash
   gh api repos/<owner>/<repo>/releases --jq '.[] | select(.tag_name=="v1.2.0") | .assets[] | [.id, .name] | @tsv'
   gh api -H "Accept: application/octet-stream" repos/<owner>/<repo>/releases/assets/<id> > ../draft-1.2.0/<name>
   ```
3. Save the draft's metadata. The `releases/tags/` endpoint returns published releases only, so select the draft from the list:
   `gh api repos/<owner>/<repo>/releases --jq '.[] | select(.tag_name=="v1.2.0")' > ../draft-1.2.0.json`
4. Run:

```bash
python packaging/verify_release.py --assets ../draft-1.2.0 --release-json ../draft-1.2.0.json \
    --candidate ../candidate-1.2.0 --version 1.2.0
```

5. Read the notes on the draft page; they must match `packaging/RELEASE_NOTES_v1.2.0.md`.

If anything fails: delete the draft (approval), fix, rebuild. If the tag must move, delete it before anything is published, record why, and push again (approval). Never move a tag after publication.

## 4. Publish

Second approval block: version, asset list with hashes, verify result. On yes:

```bash
gh release edit v1.2.0 --draft=false
```

If the session's publish call is refused (observed from cloud: 403), the owner runs this exact command on their machine; the approval already given covers it unchanged.

With immutable releases enabled in repository settings, assets and the tag are locked from this moment (documented behavior; confirm on the first release). Any later defect becomes a new patch version.

## 5. After publishing

- Download the published assets again into the project's local release folder and run `verify_release.py --expect-published --expect-immutable` against the published metadata (`gh api repos/<owner>/<repo>/releases/tags/v1.2.0`).
- Published releases do not update any host. Each host install is a separate action and a separate install-log row ([verify-and-record.md](verify-and-record.md)).
- Update the project's records: tracker, quick context, index.

## Never

- `gh release upload --clobber` or deleting and re-uploading a published asset.
- `--generate-notes` as a substitute for the reviewed notes file.
- Publishing from a session that cannot show the verify result.
