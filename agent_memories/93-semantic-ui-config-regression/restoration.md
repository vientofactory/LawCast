# Pages Runtime Restoration

## Completed Production Change

November 24, 2026, 23:22 JST: restored Pages production runtime configuration and redeployed the unchanged frontend 3.2.3 release `947c0ae19f704ee8b210e3d136e2762eced0a848`.

- Restored the semantic-search flag and attack-reload flag to `true`, original Discord URL/ID, original Hashguard URL and GTM ID (`GTM-N82SX8WB`). Public values were recovered from preserved preincident production HTML and the existing GitHub Actions variable.
- Restored the legacy fallback URL to `https://lawcast-backend.viento.me/api`. Preserved the authenticated origin at `https://lawcast-origin.viento.me/api` and its real current token recovered through SSH from `/etc/lawcast-origin/service.env`. The authenticated origin returned backend 3.2.6 before the write. The token was not printed or stored in the evidence package.
- A public-only PATCH was rejected before execution by automatic review due to possible private-binding deletion. The successful PATCH explicitly supplied all nine bindings with verified actual values, never GET-redacted secret placeholders. No setting outside production environment variables changed.
- Ran the existing `deploy-pages.yml` with `workflow_dispatch` against main. No new commit, version bump, backend rollout or root gitlink update was needed for this configuration-only redeploy.

## Deployment and Verification

[Actions run 45413070734](https://github.com/vientofactory/LawCast-Frontend/actions/runs/45413070734) succeeded; lint, typecheck, build and upload passed. Cloudflare canonical deployment `c4767e92-f3d0-411b-b1e4-474b3f8a6e79` is successful and matches the unchanged main release SHA.

- Baseline: semantic flag empty, dedicated page 303, mode controls absent; semantic API 200 with actual semantic results.
- Restored: all five dynamic public settings match their original values; dedicated page 200, mode controls present; semantic API 200, mode semantic, no fallback, three requested results; sitemap 200.
- Real browser: followed the restored semantic entry, entered `전세사기`, submitted Search and observed ten results with enabled controls. Verification tab was closed afterward.
- Separate-copy rollback restored the local public-configuration fixture byte-for-byte. Production was not rolled back. This fixture test does not simulate a Cloudflare control-plane rollback.

## Evidence

Ignored workspace `_workspace/pages-runtime-restore-20261124/` contains `MODIFIED_FILE`, `DIFF_FILE`, `VERIFICATION.txt`, executable `ROLLBACK.sh`, original SHA-256, exact baseline/modified probe outputs and deployment watch log. The four named artifacts were reopened after completion. `MODIFIED_FILE` holds only public restored values; the secret token is deliberately absent.

The existing [diagnosis](diagnosis.md) describes the earlier read-only investigation. This authorized follow-up applied the remediation.
