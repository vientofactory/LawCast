# Semantic-Search v2.5.0 Release Guard Break-Glass: title_text Loss Was Data Backfill, Not a Code Regression

## Summary

**Date**: 2026-10-12
**Workflow run**: `LawCast/actions` run `38184195199` (`deploy-semantic-search.yml`, `allow_capability_loss=true`)
**Decision**: Ship semantic-search v2.5.0 (`da6c0be`) via the documented break-glass input after diagnosing the guard failure as a **data-side artifact**, not a chunking regression.

## The Guard Failure

Runs `38167677722` and `38169291440` (root `main` pushes) failed the mandatory capability release guard:

```
capability deltas   : indexed 21177 -> 21189 | title_text 545 -> 686 | ... | derived:ai_summary 6028 -> 21059
release check       : LOST — title_text (8 notices, e.g. [2212742, 2214708, 2220960])
```

Aggregate counts improved (+141 title_text overall), yet 8 per-notice `title_text` capabilities were lost — exactly the failure mode the guard exists to catch (see `agent_memories/24-ai-summary-chunking` §4).

## Root Cause: proposalReason Backfill Replaced the Subject-Only Fallback Chunk

The 8 affected notices (`2212742, 2214708, 2220960, 2220961, 2220964, 2220969, 2221272, 2221274`) all had **`proposalReason` backfilled after the served index was built** (likms recovery, PAL backfill — lengths now 393–1736 chars; `notice_change_events` show the updates):

- **Before backfill**: empty `proposal_reason` → the chunker emitted the subject-only fallback chunk, whose TEXT is the title, satisfying the strict `title_text` oracle (score-1.0 exact-title hit).
- **After backfill**: real sections (`제안이유`, `주요내용`) are packed instead; the subject is only *prepended as embedding context*, never chunk TEXT, so `title_text` disappears under `capabilities.record_capabilities`.

### Evidence: A/B Across Chunker Versions (same records, both lose identically)

Chunked the 8 notices with the **v2.4.0 worktree chunker** (`837e077`, the currently served code) and the **v2.5.0 chunker** (`da6c0be`), scored by the same v2.5.0 oracle:

```
2212742 | v2.4.0 title_text=False (14 chunks) -> v2.5.0 title_text=False (15 chunks)
2214708 | v2.4.0 title_text=False (13 chunks) -> v2.5.0 title_text=False (14 chunks)
2220960 | v2.4.0 title_text=False (5 chunks)  -> v2.5.0 title_text=False (6 chunks)
```

**Both versions lose `title_text` on the same notices** — rolling back would not prevent the loss; the next update tick with v2.4.0 would drop the same 8. Full-set local comparison over `artifacts/chunks.jsonl` (served proxy) vs. fresh v2.5.0 chunking reproduced the CI result exactly: 8 lost, 146 gained.

## Outcome of the Break-Glass Run

The re-run took a **fresh baseline from the already-updated served index** (the 23:01 update tick had regenerated it), so the final comparison passed outright:

```
capability deltas   : indexed 21190 -> 21191 | section:제안이유 및 주요내용 15888 -> 15889 | derived:ai_summary 21060 -> 21061
release check       : OK — no capability class lost
[guard] recorded semantic-search deploy: root=02ff684e350f semantic-search=da6c0be37a3a
=== Deploy complete ===
```

`/health` now reports `"status":"ready"`, `"maxK":200`, `indexedChunks:117296`, `generation:3` — the backend v1.11.0 chunk-cap negotiation (`feat: follow the sidecar chunk cap via /health`) has a live `maxK` to follow.

## Lessons

- **A guard LOST line must be triaged against the DATA timeline before the code timeline.** Check whether the affected notices' source fields (`proposalReason`, `ai_summary`) changed between the baseline artifact build and the comparison — a backfill alone reproduces the loss under the old code.
- **The strict `title_text` oracle is sensitive to any change that fills `proposal_reason` for a previously-empty notice**: the subject-only fallback chunk is the only chunk whose text is the title, so content replacing it always costs that capability. Gains elsewhere (+146) do not offset it per-notice.
- **The break-glass input worked as designed** and the run log carries the `allow_capability_loss=true` continuation message, satisfying the "record why in the run/PR" requirement together with this note.

## Cross-References

- `agent_memories/24-ai-summary-chunking/ai-summary-chunking-measurement.md` — the 405-notice title_text regression that motivated the oracle
- `agent_memories/25-chunking-capability-gate/capability-regression-gate.md` — oracle and gate design
- `agent_memories/26-ai-summary-final-verification/readiness-verification.md` — BLOCKER items this deploy resolves
