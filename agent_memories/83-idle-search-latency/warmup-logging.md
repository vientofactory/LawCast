# Development-only Routine Warmup Logs

## Cause and patch

The 3.1.1 idle task emitted an INFO completion line for every successful native
warmup. The operational baseline captured five such lines in the preceding
60 seconds; these routine messages obscured useful production diagnostics.

Sidecar 3.1.2 introduces `LAWCAST_SEMANTIC_ENVIRONMENT`, default `production`.
Only the exact normalized value `development` enables routine completion logs.
Unset, empty, `production`, `test` and `dev` do not enable them. The optional
Compose `semantic-search/.env` is already injected through `env_file`; no root
Compose or live environment modification is necessary for quiet production.

The gate wraps ONLY the success logger call in `service/idle_warmup.py`.
Native inference, FAISS touching, timing, interval, memory-pressure guards,
active-request/update skips and shutdown joining are unchanged. Warmup failure
warnings stay visible in production. Normal search/resource and readiness logs
are not globally filtered or downgraded.

## Verification and rollback

- Full modified suite: 421 passed. Ruff check/format and agent guidelines pass.
- Subprocess configuration tests pin default production and explicit development.
- Parameterized logger tests verify five environments, confirm inference/index
  touching still execute, and preserve production failure warnings/readiness.
- Immutable original source copy: 410 passed, 4 copy-relative data skips.
- Rollback restores all 96 original source hashes on an independent copy;
  the active checkout remains modified. Original production image and deploy
  marker are retained under `_workspace/warmup-logging-20261112` on the host.
- Original config hashes and the observed prepatch warmup lines are retained.
- Postdeployment evidence belongs in local
  `_workspace/warmup-logging-20261112/VERIFICATION.txt`; verify real-container
  unset/production/development subprocess behavior, actual normal logs for
  90 seconds, stable image/restart identity and an HTTP semantic search.

Related: [release verification](release-verification.md). Production 3.1.1 idle
latency improvement was partial; this logging patch does not claim to fix its
remaining 3-minute origin API regression or additional latency variance.
