# Crawling legal notice

## Ownership and behavior

- Frontend branch: `codex/legal-notice`. Existing consultation-status changes were present before this task and remain untouched.
- `frontend/src/lib/server/legal-notices/` owns versioned JSON snapshots. `legal-notices.ts` selects a snapshot, route loaders return only the chosen body and version summaries, and `LegalNoticeDocument.svelte` renders it with escaped text, citations and return links.
- `frontend/src/lib/components/Footer.svelte` replaces the blanket public-domain assertion and links to `/legal`.
- `frontend/src/lib/server/sitemap.ts` includes the canonical route; its existing sitemap test is updated.
- Full user-facing legal research and source limitations live in [the review](../../frontend/docs/legal-review.md).

## Critical findings

- **HIGH**: Copyright Act Article 7 does not establish that all proposed bills, reasons, attachments and third-party works are public domain. Legislative notice announcements, enacted legislation, state-owned public works and private drafts need distinct treatment.
- MOLEG interpretation 09-0381 (2009-12-31) concerns a privately researched draft, not every formally submitted Assembly bill. Do not generalize it in either direction.
- Supreme Court 2021Do1533 (2022-05-12) was a criminal acquittal on its facts, not blanket approval of crawling. The official five-page court PDF was read. Other civil cases are identified through a named secondary legal commentary; their full judgments and subsequent appeal outcomes were not independently verified.
- **HIGH**: The existing crawler defaults to rotating browser identities (`backend/src/config/app.config.ts:209–222`; `backend/src/utils/browser-request-headers.util.ts:192–223`). Do not assert a product-identified search crawler, verified robots compliance, permission from the Assembly, or absence of circumvention. Runtime configuration and permissions were not audited. See [historical incident](../32-nsm-ua-block-and-probe-storm/nsm-portal-block-and-probe-storm.md).
- A public notice does not grant third-party rights or cure collection behavior. Operational permissions, request load, actual collection limits and source-specific rights need evidence separately.
- The user-specified `op@viento.me` mailbox now receives inquiry drafts through a mailto link. Its recipient/subject/body template is stored in the snapshot. Do not claim automatic sending, mailbox delivery verification or a response SLA.

## Verification and rollback

Evidence and guarded rollback are stored in `/private/tmp/lawcast-legal/VERIFICATION.txt` and `/private/tmp/lawcast-legal/ROLLBACK.sh`. Baseline fixture preserves the original footer and sitemap hashes. Rollback is exercised only on a separate copy; the working frontend stays modified. No commit, version bump, release or deployment is part of this task.

## Public-copy follow-up

The user requested removal of the corporate-reference explanation from the public sources section. The public page now omits the explanation and three corporate notice entries; the remaining eleven legal sources and bidirectional citations are preserved and renumbered. Internal research remains unchanged. Focused regression evidence is in `/private/tmp/lawcast-legal/remove-corporate-reference/VERIFICATION.txt`.

## Humanized text and versioned snapshots

- `humanize-korean` light run `_workspace/2026-11-26-001-634e/`: monolith and independent finalizer accepted the conservative revision. Final deterministic gate reports a 1.2% character change and 21.6% sentence touch, grade B, 6/6 self-checks; obligations 11->11, hedges 9->9, eleven citations and URLs preserved. No new legal research or legal conclusions were added.
- `2026-11-26.1.json` records the pre-humanization body; `2026-11-26.2.json` records the revised body. Dates describe repository recording and legal review, not retroactive deployment/effectiveness.
- `/legal` loads the current registered snapshot. `/legal/versions/{id}` is a stable permalink. Unknown IDs return 404 rather than silently using current text; no user-controlled filesystem path exists.
- Past body and source data are self-contained; version selection never overlays current citations or text on an old body. SSR sends only the selected snapshot plus version summaries. Client navigation derives its body from changing props.
- Add snapshots rather than overwriting existing files; content/source hashes for every existing version are pinned in `scripts/legal-notices.test.mjs`. The production Pages workflow runs these guards before deployment. The existing real-workerd suite now includes the legal tests.
- Authoring instructions: `frontend/src/lib/server/legal-notices/README.md`. Runtime loading uses static JSON imports and needs no new dependency, API or database. Historical versions are discoverable through normal links; the sitemap retains only the current `/legal` entry.
- This turn's baseline, modified and separate-copy rollback evidence: `/private/tmp/lawcast-legal/versioned/VERIFICATION.txt`. Runtime rollback is a development verification only; a future public legal correction should be recorded as a new snapshot rather than deleting history.

## Pre-publication consolidation

The user's latest instruction supersedes the two-draft setup above. The final body and sources are now the only initial snapshot, `2026-11-26.1.json`, labeled `최초 법적 고지`. The unpublished pre-humanization body and `.2` registration/file were removed from the public collection; `.2` now returns 404. The versioning mechanism remains for actual future changes. The initial snapshot pins the prior revised body hash `b3fdbd3f1592ee16c934577368290cdc6f01558a4cee49284726375ce75e0126`, so legal content is unchanged. Internal editing evidence remains outside the public history. Evidence: `/private/tmp/lawcast-legal/initial/VERIFICATION.txt`.

## Email inquiry follow-up

The user provided `op@viento.me` as the rights/correction contact. The unpublished initial snapshot now replaces GitHub issue instructions with email submission, minimal-information guidance and a stored `emailTemplate` (recipient, subject and multiline body). The optional section field is rendered as escaped text and a standard mailto draft link whose subject/body are derived from the same snapshot. No email is automatically sent, and no response SLA or mailbox verification is claimed. Initial public history remains a single entry; the pre-publication content hash is intentionally updated. Tests decode the draft URI and compare it with the visible template, retain all eleven references, and keep the single-version check. Evidence: `/private/tmp/lawcast-legal/email/VERIFICATION.txt`.

## TypeScript test-suite refactor

The standalone `frontend/scripts/legal-notices.test.mjs` Node suite was replaced by `frontend/e2e/legal-notices.spec.ts`, using the existing Playwright `test`/`expect` runner and the application's `LegalNotice` type. Four original checks, test names and the exact snapshot hash are preserved. `playwright-configs/playwright.legal-notices.config.ts` runs only the data checks without a browser or dev server. The standard E2E config also discovers them. `tsconfig.legal-tests.json` strictly checks both legal suites and the dedicated configuration with TypeScript 6 and the existing native compiler; the Pages deployment gate runs both compilers then the dedicated suite. No dependency, public body, schema, route or version changed. Both old and migrated suites reject a tampered snapshot on a separate fixture. Authoring docs now point at the TypeScript suite; historical command logs above remain historical evidence. Verification and guarded rollback: `/private/tmp/lawcast-legal/typescript/VERIFICATION.txt`.


## Remaining review and website defenses

- `frontend/docs/legal-review.md` now tracks seven remaining legal/operational reviews, evidence needed, applied UI measures and explicit unfinished work. Its stale GitHub contact description now matches the operator-provided mailbox.
- Preserved `.1` byte-for-byte and registered `.2` for substantive reuse, archived-record, official-submission and minimal rights-request guidance. No source, permission, runtime-compliance claim, response SLA or automated takedown was added.
- Notice detail links to the current reuse and correction sections regardless of AI visibility. Existing source actions and unrelated consultation-status edits remain intact.
- Actual mailbox delivery, source permissions/load, retention/deletion architecture and civil judgment originals still require operational/expert review. No release or deployment was requested.
- Focused evidence and separate-copy rollback: `/private/tmp/lawcast-legal/defenses/VERIFICATION.txt`.


## Robots policy follow-up

- Browser-visible PAL robots lists Googlebot/Yeti/Daumoa with `/bos/`, `/upload/` and `/napal/mypage/` exclusions; actual list/detail paths are not excluded. No wildcard or LawCast group is present.
- **HIGH**: LIKMS wildcard group disallows `/`. Its `/bill/` allowance belongs only to Yeti, not LawCast or browser identities. Both list POSTs and proposal-reason fragments fall under the generic prohibition. PAL's default LIKMS proposal-reason hydration also touches this host.
- NSM wildcard permits `/`. Local `CRAWLING_NSM_SOURCE=likms` is verified, not the production server configuration. Do not silently switch sources or claim complete permissions from robots.
- Direct curl returned 400 for PAL/LIKMS and 200 for NSM; browser-visible bodies resolved the two 400 uncertainties. Browser text copies are normalized observations, not raw HTTP response captures. Report and 44-case installed-parser proof: `frontend/docs/legal-review.md` and `/private/tmp/lawcast-legal/robots/`.


## Public-data access doctrine follow-up

- **HIGH**: Protocol disallow is not a legal finding. Public Data Act Article 3(3) prohibits obstructing access to generally disclosed public data except Article 28(1) cases; Articles 3(2)/(4)/(5), 17, 24, 26–28 and 36(3) also matter. Verified the effective 2026-08-28 full law through the official site's rendered body, not an empty HTML shell.
- Primary full judgments reviewed: Supreme Court 2021Do1533 (2022-05-12; reuse vs access restriction and actual processing impairment), 2023Do1086 (2023-10-26; unprotected evaluation URLs, quashed/remanded, not a final acquittal), 2023Do17354 (2024-04-16; protected private DB incorporating public-data inputs, conviction upheld). Do not transplant their outcomes to a government robots dispute.
- No directly dispositive Korean judgment on public-agency robots disallow versus Article 3(3) was found in this bounded search. The legal application is explicitly labeled inference. Previously cited civil cases remain secondary-source-only.
- Official Assembly integrated bill API listing 15126134 exists with unrestricted-license metadata, but HTML/attachment equivalence, coverage and detailed API terms remain unverified. Document recommends a concrete provision request/legal basis inquiry, not identity spoofing or a silent source switch.
- Expanded analysis is in frontend/docs/legal-review.md; unchanged legal snapshots and crawling code/configuration. Documentation-only proof and independent-copy rollback: /private/tmp/lawcast-legal/doctrine/VERIFICATION.txt.


## Grounded public notice revision

- Added `.3` as current; `.1`/`.2` and their pinned hashes are unchanged. Renderer, routing, source policies, crawler configuration and email request section are unchanged.
- Public copy leads with Public Data Act access/equality grounds and source-backed copyright distinctions; retains the verified access-versus-reuse holding from 2021Do1533 with a fact-specific limit.
- Secondary-only civil examples, private-draft interpretation and extended adversarial commentary remain internal/historical rather than current public copy. Five primary law.go.kr sources replace eleven mixed sources only in `.3`.
- Robots/legal distinction, privacy rights, accuracy limits and non-excludable liability remain. No permission, compliance or blanket immunity claim was added. LIKMS operational review is not resolved by this editorial change.
- Data/browser tests cover source counts per version, immutable old bodies, old/current navigation and identical rights-request guidance. Evidence: /private/tmp/lawcast-legal/grounded/VERIFICATION.txt.


## Release and deployment (2026-11-26)

- Final reviewed backend PR [254](https://github.com/vientofactory/LawCast-Backend/pull/254) merged to `4303e7fc33229e29b15bb1dc1f711a5c570729be`; release `backend-v3.2.10`. Root pointer PR [75](https://github.com/vientofactory/LawCast/pull/75) triggered successful main-push deployment run `45786456158`. Container verification reported `version=3.2.10 compiled_workers=2 no_ts_loader=true`; public `/api/version` returned `3.2.10`.
- Only after backend production verification, frontend PR [220](https://github.com/vientofactory/LawCast-Frontend/pull/220) merged to `c6aa9b5df8c6f00b8b8a8a3d93d698361b372270`; release `frontend-v3.3.0`. Production Pages run `45787647356` succeeded. Cloudflare canonical deployment `01092f6f-ab4c-456c-990a-0d5de8fd8079` reports production/success on that exact commit; public `/legal` contains `2026-11-26.3`.
- Root pointer PR [76](https://github.com/vientofactory/LawCast/pull/76) merged to `228de96928bc7ba73974e8e434fc2a7ffde15304` after PR CI passed. Both pointer commits were GPG-signed and changed only their corresponding gitlink. Memories were excluded.
- Local backend/frontend `dev` branches fast-forwarded to release commits; npm 11.13.0 full installs produced no package/lockfile changes. Root feature checkout fast-forwarded to final root main, preserving all memory WIP. Semantic-search pointer is unchanged.
- Evidence: `/private/tmp/lawcast-release-20261126/VERIFICATION.txt`. Existing LIKMS operational/legal review and inherited design-checker findings remain unresolved; deployment does not imply their resolution.

- Final re-observation: frontend main-push Web Vitals run `45787647276` and root final main-push run `45788634541` both completed successfully, all nine jobs each. Root backend and semantic-search deployment jobs both report success; public API still returns `3.2.10`.
