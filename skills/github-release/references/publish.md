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
Immutable releases: ON | OFF  (repository setting, read <date>)
Not included: publishing the draft, repository settings, host installs
```

An approval covers only what the block lists. When immutable releases are **OFF**, ask the owner once, before the first publish of the repository (or of this session), whether to turn the setting on (owner's browser, about a minute) — then record the answer in the approval block. Do not ask again in the same release. Observed: immutable releases stayed off for three skill-run releases because nothing forced the decision.

## 2. Where release actions run

Cloud agent sessions are refused these steps by two different sources: the network proxy or GitHub API (`remote end hung up`, HTTP 403 "editing releases not permitted"), and the session's own **safety classifier** (denials such as "merge without review" or "create public surface"). Both were observed repeatedly (2026-10-08 pilot, 2026-10-09 v1.7.0 and v1.7.1). Treat the refusals below as **expected: do not attempt them from a cloud session**; plan them as owner steps from the start:

| Action | Cloud agent session | Owner's machine |
|---|---|---|
| Build candidate, gate, push the release branch, open PRs, read releases | usually works | works |
| Merge the release PR | expected: refused (safety classifier, observed 2026-10-09) | GitHub web UI or `gh pr merge <n> --squash` |
| Push the tag | expected: refused (proxy, and classifier; observed 3 times) | signed-in `git` in a fresh temp clone, `core.autocrlf=false` |
| Publish the draft (`gh release edit --draft=false`) | expected: refused (API 403, observed twice) | signed-in `gh` |
| Delete a remote branch | expected: refused (observed 2026-10-09) | `git push origin --delete <branch>` |
| Repository settings (branch protection, immutable releases) | expected: refused | owner's browser or `gh`; may require the owner's **passkey ("sudo mode")** — the agent must stop and ask the owner to complete it; never ask for the credential |

Do not retry a refused step through another route; the refusal changes where the step runs, never the approval for it. Give the owner **one combined command block** per hand-off so there is one round trip, not one per step:

```text
OWNER COMMANDS — <skill> v<version>   (each line is covered by the approval named on it)
# 1. merge (approval: merge PR #<n>)
gh pr merge <n> --repo <owner>/<repo> --squash
# 2. tag the merge commit (approval: tag) — fresh temp clone, outside synced folders
git clone https://github.com/<owner>/<repo> %TEMP%\<repo>-tag && cd %TEMP%\<repo>-tag
git config user.name "<owner>" && git config user.email "<owner noreply>"
git tag -a v<version> -m "<skill> v<version>" <merge sha> && git push origin v<version>
# later, after the draft verify — 3. publish (approval: publish)  4. delete branch (approval: branch delete)
gh release edit v<version> --repo <owner>/<repo> --draft=false
git push origin --delete <release branch>      # tip <sha> recorded for recovery
```

Prefer `git push` from a real clone. If a connector/API push or a GitHub **web-UI upload** ("Add files via upload") is the only route, it can **alter file bytes** (observed 2026-10-06: a connector decoded `\u` escapes in a pushed Python file into literal characters; caught only by hash comparison). After any non-git push or web upload, before opening the PR, compare every pushed blob with the local file: `gh api repos/<o>/<r>/contents/<path>?ref=<sha> --jq .sha` must equal `git hash-object <path>` locally.

- Typical flow: feature PR (CI green) → merge → release PR with version bump **and final notes wording** (CI green) → merge → annotated tag on **the PR merge commit** (gate G1c). Any change after the merge — even a one-word notes fix — is a new PR; never commit straight to `main` and tag that.

```bash
git tag -a v1.2.0 -m "<skill> v1.2.0" <merge-commit-sha>
git push origin v1.2.0
```

## 3. Draft created → verify

1. Wait for the workflow. Confirm the release is a **draft** (`gh release view v1.2.0 --json isDraft`).
2. Download every asset: `gh release download v1.2.0 --dir ../draft-1.2.0` (drafts need an authenticated `gh`). `gh release download` uses GraphQL, which some proxies block (observed); fall back to REST, iterating the **release JSON asset list** (not a hand-written list) and asserting the count:

   ```bash
   gh api repos/<owner>/<repo>/releases --jq '.[] | select(.tag_name=="v1.2.0") | .assets[] | [.id, .name] | @tsv' > ../draft-1.2.0.assets.tsv
   while IFS=$'\t' read -r id name; do
     gh api -H "Accept: application/octet-stream" repos/<owner>/<repo>/releases/assets/$id > "../draft-1.2.0/$name"
   done < ../draft-1.2.0.assets.tsv
   test "$(ls ../draft-1.2.0 | wc -l)" -eq "$(wc -l < ../draft-1.2.0.assets.tsv)" && echo "all assets downloaded"
   ```

   `verify_release.py` prints `downloaded N of M listed assets` first; N < M is a download problem, not a release defect (observed false FAIL when a loop skipped `SHA256SUMS.txt`).
3. Save the draft's metadata. The `releases/tags/` endpoint returns published releases only, so select the draft from the list:
   `gh api repos/<owner>/<repo>/releases --jq '.[] | select(.tag_name=="v1.2.0")' > ../draft-1.2.0.json`
4. Run:

```bash
python packaging/verify_release.py --assets ../draft-1.2.0 --release-json ../draft-1.2.0.json \
    --candidate ../candidate-1.2.0 --version 1.2.0 --notes packaging/RELEASE_NOTES_v1.2.0.md
```

   It also checks that the release was created by `github-actions[bot]` with the title `<skill> v<version>`, and that the body equals the notes file.

5. Read the notes on the draft page as a reader would.

If anything fails: delete the draft (approval), fix, rebuild. If the tag must move, delete it before anything is published, record why, and push again (approval). Never move a tag after publication.

## 4. Publish

Second approval block: version, asset list with hashes, verify result. On yes:

```bash
gh release edit v1.2.0 --draft=false
```

If the session's publish call is refused (observed from cloud: 403), the owner runs this exact command on their machine; the approval already given covers it unchanged.

With immutable releases enabled in repository settings, assets and the tag are locked from this moment (documented behavior; confirm on the first release). Any later defect becomes a new patch version.

## 5. After publishing

- Download the published assets again into the project's local release folder and run `verify_release.py --expect-published --notes packaging/RELEASE_NOTES_v1.2.0.md` against the published metadata (`gh api repos/<owner>/<repo>/releases/tags/v1.2.0`), adding `--expect-immutable` when the approval block said ON. The record says which.
- **Release body after publishing.** Assets and tag are locked; the body is not. The only allowed edit is to **append** a dated section `## Known issues (added YYYY-MM-DD)` that names the defect and the fixing version; never rewrite the original text. Log the edit in the release record. `verify_release.py --notes` accepts exactly that shape and FAILs any other difference.
- Remove the project's "Release in progress" marker (gate G0) after publishing — or after abandoning the release, saying why.
- Published releases do not update any host. Each host install is a separate action and a separate install-log row ([verify-and-record.md](verify-and-record.md)).
- Delete the merged release branch (approval), recording its tip SHA for recovery; list any other remote branches whose tips are ancestors of `main` for a separate owner decision. Repositories with "automatically delete head branches" enabled (repo-setup default) skip the first step.
- Update the project's records: tracker, quick context, index.

## Never

- Creating a release by hand (`gh release create` outside the workflow, or the web UI's "Draft a new release"). If the workflow failed, fix it and re-run it on the same tag before anything is published. Observed: 4 of 12 releases of one repository were hand-created, one with a broken title; `verify_release.py` now FAILs a release whose author is not the workflow.
- Renaming a branch that has an open PR — GitHub closes the PR and it cannot be reopened (observed 2026-10-08). A renumbered candidate gets a new branch and a replacement PR; close the old PR with a comment linking forward. `--force-with-lease` only on your own un-reviewed branch, never on `main`.
- `gh release upload --clobber` or deleting and re-uploading a published asset.
- `--generate-notes` as a substitute for the reviewed notes file.
- Publishing from a session that cannot show the verify result.
