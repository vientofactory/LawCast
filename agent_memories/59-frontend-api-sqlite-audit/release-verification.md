# Backend 1.19.6 and frontend 1.25.4 production verification

## Release preparation

The owner authorized production deployment and a final measured comparison after the local-only audit. Backend PR #224 merged at `0219e2c6fa059305ca9069c6b48c76d9f01f74ea`, tag `backend-v1.19.6`. The implementation commit `7dcf172e90f823bf091d04033fe8a76fefbbc1b5` has a verified maintainer PGP signature. Backend dev was fast-forwarded to the release SHA and pushed; full npm install left the lockfile clean.

Frontend PR #174 is held until backend deployment succeeds. Signed implementation `4de8005` is version 1.25.4. No frontend production dependency is deployed early.

Pre-release checks: backend lint/type/build and 1,273 Jest tests passed, normal process exit; frontend lint/check and six real local SSR consumer tests passed; unchanged sidecar lint/format, 345 tests and index-capability integrity passed; agent guidelines passed.

Deployment and measured results will be appended after the production rollout. Before/after evidence uses the same Lighthouse browser profile and throttling settings, low-frequency external reads, and independent localhost origin read controls. Measurements do not prove identical background workloads or a field Core Web Vitals change.

## Backend deployment confirmed

[Root run 40666732295](https://github.com/vientofactory/LawCast/actions/runs/40666732295) passed both Node backend/frontend matrix jobs, sidecar and CI gate, then deployed backend successfully. The deploy log reports healthy at 2026-10-28T09:50:17.962Z and records the expected release SHA. Version/health reads independently report 1.19.6 and healthy Redis/Ollama. A native OPEN_READONLY SQLite inspection confirms the new migration is recorded, all primary-key aliases remain protected, and metadata-only EXPLAIN has no trigger Program opcode. The probe ran after deployment; it is not a pre-migration production measurement.

Frontend PR CI run 40667099100 passed, including the newly added SSR API consumer step. Frontend merge can now proceed after its backend dependency is live.
