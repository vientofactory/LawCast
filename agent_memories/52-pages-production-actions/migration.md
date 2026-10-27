# Main-only Pages Deployment Through GitHub Actions

## Scope and acceptance criteria

Replace native Git-triggered builds for `lawcast-frontend` and `gatekeeper-frontend` with main-only GitHub Actions uploads to the existing Pages projects. Preserve production domains, encrypted runtime bindings, app identity and deployment history.

- A push to main automatically checks, builds and deploys a production artifact from the exact pushed SHA.
- A non-main push creates no Cloudflare deployment record, including skipped records.
- The production environment and its deployment credential are available only to main.
- Verify both production uploads and real non-main probe pushes before declaring the migration complete.

## Confirmed native integration limitation

Both projects originally excluded all preview branches through a custom `*` exclusion. Changing `preview_deployment_setting` to `none` still produced a skipped deployment from a test branch, with `skip_reason=preview_deployments_disabled`. The temporary branch and record were removed. Disabling preview builds alone is insufficient to prevent records.

## Implementation

Each frontend owns `.github/workflows/deploy-pages.yml`. It triggers on main pushes or a main-only manual dispatch, uses read-only GitHub contents permissions, a production environment restricted to main, pinned Node/npm and pinned existing Wrangler versions. Only the deploy step receives the Cloudflare token. Uploads explicitly use `--branch main` and `--commit-hash "$GITHUB_SHA"`. Non-main triggers and PR deployment steps are absent.

Wrangler is promoted from an existing transitive dependency to an exact direct dev dependency; package version bumps are patch maintenance releases. Runtime secrets remain encrypted in Cloudflare and must never be round-tripped as masked empty strings.

Public build-time values are copied from verified production output into GitHub Actions Variables: LawCast's `PUBLIC_GTM_CONTAINER_ID`, Gatekeeper's `PUBLIC_GATEKEEPER_API_BASE_URL`, and the non-secret Cloudflare account ID. The other runtime bindings remain on Pages.

## Cutover order and current status

1. Prepare and validate workflows, versions, locks and main-only environment policies.
2. Provision separate Pages Write deployment tokens as environment Secrets. Credential creation through the browser requires an explicit action-time confirmation; no token values belong in source or notes.
3. Publish the workflows through each repository's normal PR path.
4. Disconnect native Git integration only after the Actions deployment path is ready. Keep the projects and domains intact.
5. Verify production Actions deployments, then push/delete temporary non-main branches and compare deployment lists before/after.
6. Synchronize released child SHAs and metadata repository pointers; document final evidence.

Current status: deployed and verified. Both main-push and independent post-disconnection Actions deployments succeeded. Two explicitly approved Pages Write credentials are stored in main-only production environment Secrets; private temporary files and clipboard values were removed. Native Git sources were disconnected through `DELETE /accounts/{account_id}/pages/projects/{project_name}/source`; domains and encrypted runtime binding keys were unchanged.

## Final evidence (2026-10-28)

- LawCast feature/release: [PR 171](https://github.com/vientofactory/LawCast-Frontend/pull/171), [frontend-v1.25.1](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.25.1), exact main/dev SHA `b7d79b7f4dc23e636031b77d8a63072285288d5d`.
- Gatekeeper integration/promotion: [PR 54](https://github.com/vientorepublic/gatekeeper-frontend/pull/54), [PR 55](https://github.com/vientorepublic/gatekeeper-frontend/pull/55), [v1.0.2](https://github.com/vientorepublic/gatekeeper-frontend/releases/tag/v1.0.2), exact main/dev SHA `0933ce306effd70d76c25c1e3a3c002de99b8e8c`.
- Main-push Actions succeeded: LawCast run `40572396008`, Gatekeeper run `40572412930`.
- After source disconnection, main manual-dispatch Actions also succeeded: [LawCast run 40572775703](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40572775703), [Gatekeeper run 40572780596](https://github.com/vientorepublic/gatekeeper-frontend/actions/runs/40572780596).
- Production deployment IDs: LawCast `6229f8f6-9482-484b-8344-3dd353290485`, Gatekeeper `8dd163fd-f84a-4b6a-bbfa-43a14bbce0c8`; both `ad_hoc`, branch `main`, exact release SHA, successful.
- Actual disposable `renovate/pages-actions-record-check-20261028` branches were pushed from each released SHA without creating commits. Before/after full deployment ID sets were identical: LawCast 96, Gatekeeper 13. Both had zero non-main records and unchanged canonical deployments. GitHub Actions returned no runs for either probe branch. Probe branches were deleted afterward. Native preview records created earlier during migration were removed.
- Actual dev restoration pushes also occurred after disconnection. Frontend working trees are clean and main/dev/tag tips agree. Existing unrelated LawCast backend edits remain untouched.
- Production curl checks returned 200 for both sites; LawCast's GTM and branding and Gatekeeper's public API base matched the pre-cutover production values. No real-user OAuth flow or production key mutation was performed.
- Local checks: clean npm 11.13.0 installs; lint and Svelte checks passed; Gatekeeper 19 tests and both adapters passed; LawCast Cloudflare build passed; actionlint 1.7.12 and both guideline scanners passed. Promoting the pre-existing Wrangler versions to exact direct dependencies changed no resolved package versions.

The LawCast root gitlink in this change pins the released frontend main/dev SHA. Gatekeeper's corresponding metadata change records its released child SHA through its normal feature/dev/main path.
