# Backend 3.2.9 release verification

## Released state

Date: 2026-11-26 (Asia/Tokyo).

- Backend PR [253](https://github.com/vientofactory/LawCast-Backend/pull/253), release [backend-v3.2.9](https://github.com/vientofactory/LawCast-Backend/releases/tag/backend-v3.2.9).
- Backend main/tag/root gitlink: `ceffdf2ccd90aa5f863e7b905c2c720804c96f83`. Version manifests both contain `3.2.9`; the installed lockfile dependency tree is unchanged.
- Root PR [74](https://github.com/vientofactory/LawCast/pull/74), merged main `504b47646f8d10ffe4d13c788623014a6c957100`. The PR changes only the backend gitlink.
- Actual main **push** CI [45762465636](https://github.com/vientofactory/LawCast/actions/runs/45762465636) completed **success**. Both deployment jobs completed success, not skipped.
- PR CI [45761906148](https://github.com/vientofactory/LawCast/actions/runs/45761906148) also passed. Its deployment jobs were correctly skipped and were not treated as production evidence.

Source commits `19b875727cb6a935cfdeb901d41172f687813845` (backend) and
`c82bb0b004e45cc7edb908535a555db5e717c97c` (root) were created with explicit
`git commit -S`; both locally verify as `G` with the maintainer's configured
PGP signing subkey. GitHub verified the backend commit as valid.

## Required order and gates

1. Created isolated main-based worktrees, applying only the verified SQL patch.
2. Before versioning, passed backend lint, API/native TypeScript, build and all
   1,450 tests; frontend main lint/check; sidecar ruff, **421 pytest tests** and
   the index-integrity/capability report (125,046 chunks / 22,685 indexed notices).
3. Checked tags, bumped 3.2.8 to 3.2.9 and ran a real npm 11.13.0 install.
   JSON comparison proves only the version fields changed in package manifests.
4. Re-ran the final release gates: **112 suites / 1,450 tests**, exit 0.
   The earlier local audit's 1,461 count included 11 uncommitted health tests;
   those unrelated changes were deliberately excluded from the release.
5. Signed/pushed backend feature commit, checked the successful GitGuardian check
   and absence of unresolved review threads, squash-merged PR 253, created the
   matching GitHub Release, and verified tag = origin/main = release SHA.
6. Returned backend and frontend to persistent `dev`, fast-forwarded only, pushed
   the dev refs and ran npm 11.13.0 installs. Neither lockfile is dirty.
7. Signed a root feature commit containing only the released backend gitlink,
   passed PR CI, merged PR 74, and watched the distinct main push execution to completion.

No health/frontend WIP was committed or deployed. **40 unrelated modified
or untracked files** retain their pre-deploy SHA-256 hashes. Both submodules stay
on `dev`; root and submodule release pointers match without a `+`/`-` status prefix.
Frontend and semantic-search gitlinks remain unchanged. No shared branch was deleted.

## Actual production evidence

The backend deployment log contains these literal successful gates:

```text
APP_VERSION=3.2.9
Backend runtime: v24.22.1 (expected v24.22.1)
Backend release verified: version=3.2.9 compiled_workers=2 no_ts_loader=true
```

The unchanged semantic-search job exited through its existing service-change guard:

```text
=== No semantic-search changes since last deploy; early exit ===
```

It completed successfully without rebuilding the unchanged sidecar. No capability
loss override or CI/deployment guard bypass was used.

Five read-only public API probes via `https://law.viento.me`, each with a unique
cache-busting release parameter and a 20-second deadline, returned HTTP 200:

- `/api/version`: version=3.2.9; 408 ms.
- `/api/health`: version=3.2.9, health=healthy, dependencies={'redis': 'up', 'ollama': 'healthy'}; 288 ms.
- `/api/notices/archive?page=1&limit=2&isDone=false`: items=2, total=1640, isDone=False; 234 ms.
- `/api/notices/archive?page=1&limit=2&isDone=true`: items=2, total=21232, isDone=True; 307 ms.
- `/api/notices/changes?page=1&limit=2`: items=2, total=35379; 241 ms.

The health response reports Redis up and Ollama healthy. Both archive completion
filters return only matching items; change listing remains functional. These are
post-deploy smoke observations, not a production latency SLO or exhaustive live
write test. SQL parity, migration up/down/up and write/integrity invariants were
validated on disposable databases before deployment.

## Reproducible release rollback evidence

The updated copy-only `ROLLBACK.sh` restores all nine original file hashes
(seven source/test files plus two version manifests), removes the five added
files, and restores version 3.2.8 in a disposable release-source copy. The restored
copy passes **15 affected suites / 233 tests**, exit 0. Actual production remains
3.2.9; no production rollback was executed.

An operational rollback would be another reviewed root-pointer release to the
prior backend release commit `82c95265ba87c42c09db7c187f95b5729f9378a4`, followed by
its actual push deployment gates. The index-only migration is compatible with the
old application; its tested down method restores the prior index definitions if
explicit schema rollback is required.

## Evidence artifacts

- `_workspace/sql-deploy/deploy-run.json`: completed push execution and every job.
- `_workspace/sql-deploy/backend-deploy-job.log`, `sidecar-deploy-job.log`: actual deployment gates.
- `_workspace/sql-deploy/production-smoke.json`: five observed endpoint results.
- `_workspace/sql-deploy/release-tests.log`, `release-rollback-tests.log`: exact test outputs.
- `_workspace/sql-audit/VERIFICATION.txt`: exact commands, inputs, outputs, exit statuses and artifact paths.
- `_workspace/sql-audit/MODIFIED_FILE.tar.gz`, `DIFF_FILE.patch`, `manifest.json`, `ROLLBACK.sh`: final versioned sources, preserved originals and copy-only rollback.
