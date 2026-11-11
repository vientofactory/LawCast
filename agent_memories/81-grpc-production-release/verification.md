# gRPC Services 3.1.0 Production Release

## Sequence

1. Release the validated sidecar and backend repositories through signed
   feature commits and squash PRs. Root CI validates both wire-contract
   owners together before any production cutover.
2. Stage the validated FP32 query bundle and environment backups within
   /root/lawcast. Keep project-external host files unchanged.
3. Root deployment verifies sidecar HTTP readiness, gRPC readiness and
   index capability preservation before deploying the gRPC backend.
4. Verify the live backend and only then merge the frontend release,
   which triggers the existing production Cloudflare Pages workflow.
5. Verify deployment identities and return local backend/frontend to dev,
   semantic-search to main, and record only release-reachable gitlinks.

## Deployment controls

The backend deploy job now depends on the sidecar deploy job. Both already
share a remote-checkout concurrency lock. Deployment markers move into
the ignored _workspace/deploy-state directory rather than writing a
sibling directory outside the project. The sidecar deploy explicitly
probes the internal gRPC health method before it can unblock the backend.

Local gates: 1,330 backend tests, 390 sidecar tests, 57 search UI browser
tests, both service production builds, lint/type checks, and the local
index integrity/capability report. Release evidence is kept in the ignored
_workspace/release-20261111 directory; remote backups stay in the same
directory beneath the production checkout.
