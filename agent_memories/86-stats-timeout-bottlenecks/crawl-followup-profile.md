# NSM Sighting Write Scheduling

## Production attribution

Backend 3.2.0 still delayed ordinary HTTP requests during list-sighting metadata writes. The original 19 five-second timeouts followed the completed all-bill scan at 10:59:42 UTC on 2026-11-12 and preceded the 16,021-sighting completion at 11:01:22; the automatic audit started later at 11:03:47. Do not attribute that episode to the audit child.

A follow-up production CPU profile (12:27:42–12:34:42 UTC) sampled 57.8 seconds in synchronous better-sqlite3 `run`. A 30-second bin in the sighting phase contained 29.3 seconds of `run` and no idle samples. This is blocking wall occupancy, including I/O wait, not 57.8 seconds of exclusive CPU. The matching NSM-running full-stat p95 was 4,158 ms (20 requests); the observed runtime-window-max p95 was 575 ms (36 windows). SQL-level write correlation and concurrent-audit evidence are retained locally, with final operational results in [backend PR 244](https://github.com/vientofactory/LawCast-Backend/pull/244).

## Fix and invariants

`backend/src/modules/notice/notice-archive.service.ts` bounds `NSM_LIST_SEEN_STAMP_CHUNK_SIZE` to five instead of 100 and yields with a one-millisecond timer between batches. `await` on the synchronous driver and an immediate-only yield are not a bounded latency budget. Metadata updates share SQLite row pages with large immutable HTML and screenshot payloads; a small SET list is not a small I/O operation. The ID-first query plan already seeks `idx_notice_archives_notice_num`, so adding another eligibility index is not the fix.

Preserve every valid ID, deduplication, monotonic timestamps, accumulated affected count, and complete stamping before deletion candidate selection. Never disable source detection, skip sightings, alter immutable payloads, or move the full audit back to the main loop to make latency charts look better. The independent timer-progress/batch-size regression runs on a fully migrated real SQLite schema in `notice-archive-nsm-list-absence.spec.ts`.

## Measurement requirements

Report actual simultaneous PAL/NSM-running plus audit samples separately from generic background activity. At least 20 full-stat responses and 20 deduplicated runtime windows are required; list-sighting write-phase coverage must also be shown explicitly. Keep errors, dropped arrivals, boundary exclusions, profiler overhead, image/config identities and incomplete observations visible. Sampled histogram maxima are not a reconstructed global p99. Full-audit correctness requires the complete report and zero failures, not a healthy HTTP response during only the final minute.

Raw profiles, SQL shapes, disposable DB copies and request traces remain under ignored `_workspace/`. Never stage those files or unrelated frontend work. See [release invariants](release.md) and [metadata-write guard](../59-frontend-api-sqlite-audit/verification.md).
