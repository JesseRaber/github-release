# Distribution scope and licensing

Use this before repository setup or preparing a release, and whenever an edit changes ownership, sharing, licensing, attribution or promotion. Record the owner's decision in the project's canonical records. Do not infer public intent from GitHub, an existing release workflow, a package format or the word "release". Reuse an explicit current decision; ask only when the intended audience or rights are unclear.

## Establish the scope

Record: owner; private/owner-controlled or public audience; authorized internal users, organization, accounts/tools and other recipients; allowed uses and distribution; selected terms/license; preserved third-party notices and prior grants; approved attribution and optional website/storefront links; evidence of the owner's decision. Visibility, license and permission to perform a release are separate decisions. Unknown audience or conflicting terms blocks distribution, not independent local inspection or drafting.

## Private or owner-controlled

- Respect explicit no-sharing boundaries. Keep skill contents, private examples and derivative skills within the owner-selected internal/private audience and uses, including approved internal organization users and authorized AI processing. Private does not automatically mean owner-only. Sanitizing or summarizing does not authorize external sharing.
- Use the owner's approved ownership/confidentiality terms. Do not apply MIT or another permissive license by default. Review LICENSE, README, SKILL.md, plugin metadata, package contents and release/install guidance for contradictory grants or promotion.
- Permit the owner's and approved internal users' authorized use and adaptation across approved tools. Do not make notices prevent that use. Preserve third-party notices and rights already granted; changing future terms does not retroactively revoke earlier grants. If rights ownership is unresolved, flag it before licensing/distribution rather than asserting ownership of third-party material.
- Keep public promotion, SEO/discovery campaigns and storefront links out of private packages. A private repository or draft release does not prove that inherited folder links, collaborators or provider/account settings are restricted. Inspect access only within authorization; report gaps and obtain explicit access-change scope and any mandatory action-time confirmation before changing access.
- Notices express policy; they do not prevent copying or prove confidentiality. Never claim copy-proof protection or verified owner-only access from a notice alone.

## Public

- Preserve intentional sharing. Public visibility does not itself select an open-source license; record the owner's intended reuse rights and approved license, retaining applicable notices.
- Make the purpose and supported use cases clear in the description and README. Use relevant, accurate topics/keywords; useful quick-start instructions, examples and limitations; consistent author attribution; and owner-approved website/storefront links where helpful. Do not invent links, stuff unrelated keywords or promise exposure/search rankings.
- Review rendered documentation, examples and public assets for accuracy and private information before sharing. Promotion/storefront work belongs only to public skills and remains within the approved scope; setting repository topics, Website fields, social images or publishing promotional material requires the corresponding authorization.

## Release check

Confirm that the selected source revision, licenses/notices, README, entrypoint, plugin metadata, package members, destination and release visibility all match the recorded audience and rights. Host formats that omit LICENSE still need an approved plain-language boundary in the entrypoint; do not silently strip required third-party notices. Record mismatches and stop the affected release step until resolved. Preserve historical release bytes. A local policy edit does not update remote repositories, existing ZIPs or installed skills. Name those remaining alignment tasks explicitly.

Every action still needs explicit scope coverage under [approval scope](approval-scope.md); one owner approval may cover multiple ordinary steps. Settings/access and mandatory host confirmations retain their safeguards. This reference authorizes none of those actions.

## Private editions of an existing public skill

Keep the public reusable source and existing grants intact. A private edition is
an independent owner-approved destination, not permission to change public
visibility or retract prior releases. Decide repository owner/name, audience,
terms, selected source revision and host rollout before creating or deploying it.
One private collection or separate repositories are both valid; choose based on
access boundaries and release cycles rather than assuming either arrangement.

Use a reviewed current-file snapshot with fresh private history if that is the
chosen design. Retain required notices and exact upstream commit provenance;
do not import private logs, credentials, old archives or Git history by accident.
Separate reusable instructions from owner-specific paths/scenarios/configuration.
Do not assume hosts support overlays: use distinct skill names, or an explicitly
approved replacement strategy, then check every discovery root for duplicates.

Pilot one skill on one named host. Preserve a verified backup outside discovery
roots, bind the package/source hashes, test actual fresh-session load and bounded
behavior, and define rollback before expanding the rollout. File presence alone
is not adoption. Keep credentials in the proper runtime secret store, not even
in a private repository.

For improvements returning to public source, reconstruct a small reusable diff
against the public base. Deliberately review file names, metadata, links,
examples, generated packages and disclosure boundaries before a public push.
Never merge or mirror private history into public source. Reuse a current
approval covering this concrete sanitized contribution; private development
approval alone grants no public disclosure. Generic guidance here creates no
private repository, deployment or cross-project policy adoption by itself.
