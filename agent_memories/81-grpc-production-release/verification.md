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

## Origin deployment evidence

- Sidecar PR 24 and backend PR 238 release 3.1.0; the signed squash commits
  are `37731e533078bd7b40c4c8b86ff9dd92c93c02b6` and
  `6d5a43df32cebda070e2b46208e9fae48e1db24c` respectively. GitHub reports
  both commit signatures as verified/valid.
- Root PR 44 passed CI and merged as
  `9a1071c0f4e930e2e9d43e910c232ecc4cb426c3`.
  [Production run 42971672776](https://github.com/vientofactory/LawCast/actions/runs/42971672776)
  passed both Node matrices, Python tests, the capability comparison and
  the ordered service deployments. The comparison reports `capability deltas : none`
  and `OK — no capability class lost` for 22,271 notices.
- The production backend reports 3.1.0 and Node v24.22.1. Both semantic and
  board semantic searches return HTTP 200 with no fallback; matching sidecar
  logs show `transport=grpc`. Production intentionally does not expose the
  development-only timing response header.
- Direct HTTP/gRPC sidecar comparison preserves all five clear chunk IDs:
  `2209590-0004`, `2214484-0015`, `2203263-0020`, `2217510-0000`,
  `2214122-0009`. The public semantic result notice ordering also matches
  the pre-deploy baseline. Both weak-result lists match between transports.
- The ONNX bundle matches all four manifest hashes at pinned model revision
  `7074d66aa46562342193ca4feb3d89bf9dad71b4`. Runtime logs confirm
  `query-encoder=onnx cpu_threads=2`, probe delta `3.42726707e-07` and
  `torch_weights=deferred`. No PyTorch fallback remains after correction.

## Release prerequisites corrected

The first frontend PR CI exposed the existing 342px mobile reading-width
assertion failing at 334px after the comparison-panel padding change.
The mobile hunk boundary now expands by 4px on either side, retaining the
12px inner padding and all desktop layout rules. The unchanged width
assertion and four compact-comparison viewport/theme cases pass, as do
all 57 search UI cases after the correction. No assertion was relaxed.

macOS tar resource metadata created `._*` AppleDouble files in the staged
production tokenizer folder. Although the four content hashes matched,
the strict tokenizer inventory guard correctly rejected those extra files
and selected PyTorch. Only the transfer-generated metadata was removed;
the full inventory and hashes were rechecked before restarting the sidecar.
The restart confirms ONNX and deferred PyTorch weights. Future cross-platform
bundle packaging must exclude AppleDouble metadata or use Python tarfile
with an explicit manifest-based file list.

The operational rollback script was executed against a separate project-local
fixture with a recording Docker shim, not against the production services.
All original Compose/env bytes were restored; the newly added root `.env`
was removed; expected image-tag and Compose commands were recorded. Old
service images and private env backups remain under the project release
workspace, and the deployment marker no longer writes outside the project.

## Frontend release and final pointers

[Frontend PR 203](https://github.com/vientofactory/LawCast-Frontend/pull/203)
passed its complete [PR CI 42972124181](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42972124181)
after the mobile width correction, then merged only after origin runtime
verification. Commit `955fd7c8be518b3c14bcd85ef9b40d36fa849c6b` is the
`frontend-v3.1.0` release, synchronized to `origin/dev` by fast-forward.
A real npm 11.13.0 install left the lockfile clean. Backend dev is likewise
synchronized, and the sidecar remains on main. All three final root
pointers name these release commits, not feature-only commits.

Production Pages deploy is [run 42974317808](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42974317808).
The exact merged frontend tree also runs the full postmerge regression
workflow [42974317737](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42974317737).
