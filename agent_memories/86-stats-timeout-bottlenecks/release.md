# Statistics Latency Release

## Implementation invariants

- Summary-backfill cursor hydration must seek the already-selected notice IDs, select `lifecycleStatus`, and retain only active archives before joining. Adding a lifecycle predicate to this bounded hydration query can make SQLite scan the lifecycle index instead of seeking the unique notice-number index. This exception does not remove lifecycle guards from other eligibility queries.
- Keep the original summary-state `cursorCount`, source ordering, and page limit. Missing, deleted and renumbered archives must not terminate a cursor scan early. Continuing pages yield to the event loop.
- Linux browser enumeration uses bounded asynchronous procfs reads. Preserve lease ownership, zombie handling, shutdown cleanup, and the portable fallback; do not restore a fork/exec on every normal Linux lease snapshot.
- Cache immutable cron descriptions, not crawler status. Slow-stat stage durations are inclusive wall time and overlap; do not sum them as exclusive CPU or SQL time.
- `GET /api/stats?view=runtime` reads existing event-loop and memory telemetry without waiting for DB, Redis or Ollama aggregation. Default full statistics and the home projection remain compatible.

## Regression gates

The release requires backend lint, both TypeScript compilers, build, full Jest, frontend checks, the existing sidecar checks and capability report, and the agent-guideline checker. Security Review found no high-confidence vulnerabilities. Real SQLite tests preserve active/missing/deleted/renumbered and cursor semantics; HTTP tests cover runtime telemetry while an external health dependency waits.

Full change-chain audits remain supervised, readonly child-process work, without a main-loop fallback. Both workers remain ordinary TypeScript build/lint inputs. Polling rate-limit failures must be counted separately from transport/server failures.

## Release and operational evidence

Target: backend 3.2.0 ([backend PR #243](https://github.com/vientofactory/LawCast-Backend/pull/243)). The backend feature PR and root gitlink PR use signed commits and the normal CI/deployment gates. Only the backend gitlink changes; unrelated frontend work is not released. Release and postdeployment measurement summaries are recorded in the PR discussion and final task result.

Raw profiles, probes, archives, diffs and local verification transcripts belong in ignored `_workspace/`, not in project history. Prior untracked session material was preserved there before cleanup. Only this concise implementation memory is retained in Git.
