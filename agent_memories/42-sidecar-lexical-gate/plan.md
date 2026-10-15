# Sidecar Lexical-Evidence Gate Wiring Plan

How the `hybrid.py` lexical-evidence gate (session 42, `semantic-search/lawcast_semantic/hybrid.py`)
reaches the serving path so unrelated queries get explicit empty results.

## 1. Deciding constraint (verified in code)

`SemanticSearchService.collectChunkWindows`
(`backend/src/modules/semantic-search/semantic-search.service.ts:331`) stops
widening when `window.results.length + windowWeak.length < chunkK`
(`corpusExhausted`). Per-window filtering inside the sidecar would fake
exhaustion: the first gated window returns short, widening stops, and the
backend serves fewer candidates than the corpus holds. Therefore the sidecar
must **annotate, not filter**; the backend gates **post-accumulation** in
`searchSemantic`, never inside the window loop.

## 2. Wire changes (all additive, no shape break)

1. **Sidecar** (`semantic-search/service/app.py`): `SearchHit` gains
   `lexicalEvidence: bool`, computed per hit via
   `hybrid.has_lexical_evidence(query, chunk)` against
   `searcher.chunks_by_id[result.chunk_id]`. Cost is regex tokenization over
   short strings, negligible next to embedding + FAISS. Field name pinned in
   the cross-language contract spec both sides (same commit, per AGENTS.md).
2. **Backend types** (`semantic-search.types.ts`): `SemanticSidecarChunk`
   gains `lexicalEvidence?: boolean` (optional). An older sidecar omits it
   and the service treats unknown as `?? true` (evidence assumed): fail-open,
   current behavior preserved during rollout.
3. **Backend gate** (`semantic-search.service.ts`): applied in
   `searchSemantic` after `collectChunks` returns. `toNoticeHits` carries one
   evidence flag per notice (OR over its chunks). Modes via
   `semanticSearch.lexicalGate`: `off` | `shadow` | `enforce`.

## 3. Empty-result contract

A gated-empty answer keeps the existing wire shape: `mode: 'semantic'`,
`fallbackReason: null`, `results: []`, `weakResults: []`. No keyword
substitution (session 14 invariant: an empty clear tier is the engine's real
answer) and no frontend change (empty state already renders; reveal button
hides when weak is empty). Observability is a backend log line, and the
hybrid board meta keeps `candidateTotal` pre-gate.

## 4. weakResults handling

Gate each tier independently and preserve order, then slice to k:

- Clear has evidence, weak does not -> weak `[]`, reveal button hidden.
- Clear emptied but weak has evidence -> `results: []` + reveal button with
  evidence-backed weak hits (correct: no clear results, related ones behind
  reveal).

## 5. Paraphrase safety (false rejects)

Pure-paraphrase valid queries share zero surface tokens, so an unconditional
gate would empty them. Enforce mode needs, in order:

1. Calibration on the 3-class label set (answerable / in-domain-unanswerable
   / OOD) plus the 61-query set; ship only with a measured false-reject rate.
2. A high-confidence bypass: skip the gate when top-1 dense score is at or
   above a calibrated clear-match bar (value TBD by the calibration above).
3. Alias expansion (already shipped) keeps covering the acronym class.

Never raise `MIN`/`CLEAR_SIMILARITY` as a substitute (session 20 §10.4: no
separating absolute floor exists).

## 6. Rollout order

1. Sidecar flags + contract spec + backend types, gate `off` -> release.
2. `shadow` mode: log `lexical-gate-shadow {queryHash, clearTotal, clearKept,
   weakTotal, weakKept, wouldEmpty}`, serve unchanged. Measure live.
3. `enforce` behind config after calibration; monitor empty-rate.
4. A future cross-encoder reuses the same gate point (rerank score joins the
   evidence decision); retrieval stays hybrid dense + FTS with `rrf_fuse`.

## 7. Calibration measurement (2026-10-15, live KURE-v1, 117,921 chunks)

Harness (gitignored, host-local): `_workspace/lexical_gate_eval.py`
(transcript `_workspace/lexical_gate_out.json`). 40 labeled + 61 natural
(citizen24 + news37 from `_workspace/ab_after.json`) + 5 vague-valid + 5
noise, top-15 dense window per query.

| set | n | gate empty (min_shared=1) | empty (min_shared=2) | floor 0.45 / 0.55 empty |
| --- | - | ------------------------- | -------------------- | ----------------------- |
| labeled 40 | 40 | **0** | 8 | 0 / 2 |
| natural citizen24 | 24 | 1 (`돈 관련 법`) | 7 | 0 / 1 |
| natural news37 | 37 | **0** | 7 | 0 / 0 |
| vague-valid | 5 | 3 | 4 | 0 / 2 |
| noise | 5 | 1 (`asdfghjkl` only) | 3 | 2 / 5 |

- **False rejects (min1)**: 0/40 labeled emptied; of 22 labeled targets
  reachable in the window, 21 retained. The single gate-damaged query is
  `백화점이 납품업체 갑질하면 어디에 신고해요?` (top-1 0.535, target in
  window but sharing zero tokens with it) — the paraphrase class that needs
  a cross-encoder, not a looser gate.
- **min_shared=2 rejected**: empties 8/40 labeled including `조세특례제한법
  개정` at top-1 0.85. Single-token evidence stays the shipped rule.
- **Noise rejection is weak (1/5)**: generic query tokens (`오늘`,
  `전략`, `계획`, `일정`, `우리`, `이주`, `화성`) substring-match corpus
  prose, so one shared token proves little. Follow-up: IDF-weighted
  evidence or corpus-frequency stopwords — do not raise min_shared.
- **Threshold comparison reproduces §10.4** on the new 117k-chunk set:
  labeled top-1 min 0.535 vs noise max 0.536 — still no separating absolute
  floor (0.45 takes 2/5 noise with 0 valid cost; full noise rejection at
  0.55 costs 2 labeled + 1 citizen + 2 vague).
- **Bypass bar**: no top-1 bar separates valid from noise (0.535/0.536
  overlap), so the bypass cannot fix the one gate-damaged query either. Its
  role is protecting high-score hits under future stricter variants, not
  current min1 damage. Calibrate its value only together with such a
  variant.

## 8. Three-mode E2E matrix (2026-10-15, live :8300/:3001/:5173)

14 queries (5 noise / 6 valid / 3 vague) against the backend in each
`SEMANTIC_SEARCH_LEXICAL_GATE` mode. Two methodology incidents, both caught
and redone: the first `off` run raced server startup (12 rows were error
shapes counted as empty), and the rerun hit the `expensive` rate limit
(30 req/60 s, HTTP 429) — the valid matrix paces 5 s between queries.

| finding | value |
| ------- | ----- |
| shadow == off responses | **14/14 identical** (shadow only logs) |
| enforce changes vs off | 6/14 queries |
| `asdfghjkl` | weak-5 reveal -> explicit empty, no fallback |
| vague (`돈 관련 법`, `그거 어떻게 되나요`) | emptied (intended) |
| `오늘 점심 메뉴` | 5 -> 4 (generic-token partial, known min1 limit) |
| valid queries | all served; `중처법` (alias) and `지방의회법 제정` unaffected |

**E2E-found recall bug (fixed same session)**: notice evidence first used
only the representative chunk, so `공장에서 일하다 다쳤는데` lost its rank-1
ground truth (2213578). Fixed to OR-over-all-chunks
(`toNoticeHitsWithEvidence` + unit test). The query's chunks still share
zero surface tokens (colloquial vs formal wording), so a second fix adds
the calibrated bypass: skip the gate when dense top-1 >=
`SEMANTIC_SEARCH_LEXICAL_BYPASS_SCORE` (default 0.6 — 0/5 noise bypass,
35/40 labeled + 57/61 natural bypass on the 111-query set). E2E after both
fixes: the factory query serves `[2213578, ...]` (5 hits) while `asdfghjkl`
stays fully empty. Backend suite 67 passed (5 suites).

## 9. KURE-Reranker-nano pilot (2026-10-15, sampled corpus)

Harness (gitignored): `_workspace/reranker_pilot.py` (transcript
`_workspace/reranker_pilot_out.json`). Corpus: 10 target + 100 distractor
notices from `backend/lawcast.db`, real KURE-v1 dense top-30, then
`nlpai-lab/KURE-Reranker-nano` (149M, ModernBERT, downloaded on demand)
over the 30 pairs. 15 queries (10 valid incl. alias/paraphrase/vague + 5
noise).

- **Reject signal separates where cosine cannot**: rerank top-1 valid min
  +0.07 vs noise max -6.06 (6-point gap). Dense cosine on the same pairs
  overlaps (noise up to 0.45, vague-valid from 0.48). A rerank-score cutoff
  near -2 is the first calibrated candidate for the no-result gate.
- **Rank order**: dense rank-1 held after rerank in 8/10. The 2 demotions
  (`개인정보 함부로…`, `환경 보호`) both dethroned dense tops that look
off-target on inspection (대부업법, 자연공원법) — rerank may improve
  precision, but this needs a labeled full-corpus A/B, not a 10-query read.
- **Latency** (MPS, batch 32, 30 pairs): 566–1193 ms/query; dense path
  40–257 ms. Prod CPU will be slower — measure in the CPU docker image with
a top-20 window before promising any SLO (backend timeout is 10 s).
- Decision: pilot YES, rollout NO. Next: IDF-weighted lexical evidence
  first (near-zero cost), then full-corpus rerank bake-off
  (nano vs bge-reranker-v2-m3) with rank + calibration + CPU latency.

## 10. Full-corpus bake-off (2026-10-15): nano vs bge-reranker-v2-m3

Harness: `_workspace/reranker_bakeoff.py` (`dense` then `rerank <model>`;
transcripts `reranker_bakeoff_{dense,nano,bge}.json`). Live 117,921-chunk
index, dense top-30 window, 40 labeled + 5 noise + 5 vague queries.
Rerankers forced to `device=cpu` (batch 8) to simulate the production sidecar.
Methodology fix: bare `python` segfaulted (exit 139, faiss+torch libomp) —
`OMP_NUM_THREADS=1` per `lawcast_semantic/omp_env.py` fixed it.

| metric (40 labeled) | dense | nano (149M) | bge-v2-m3 (568M) |
| ------------------- | ----- | ----------- | ---------------- |
| recall@1 / @3 / @5 | 0.150 / 0.450 / 0.500 | **0.300** / 0.450 / 0.500 | 0.225 / 0.450 / 0.525 |
| MRR | 0.300 | **0.380** | 0.346 |
| noise/vague top-1 band | overlap (0.43/0.48) | labeled min -0.83 vs noise max **-1.36** (clean split ~-1.0) | labeled min 0.03 vs noise max 0.04 (overlap) |
| CPU latency med/max (30 pairs) | — | **1332 / 1856 ms** | 2854 / 4091 ms |

- 15/40 targets moved; typical fixes: `한은 전북 이전` 4→1,
  `가맹 본사 갑질` 16→8, `청년 일자리` 13→5. Absolute levels stay low
  (same-title competition, session 20 §3) — deltas are the signal.
- Vague queries span both bands under either model (vague is the overlap
  zone for every signal tried so far).
- **Winner on all three axes: KURE-Reranker-nano** (same lab as KURE-v1,
  4x smaller, 2.1x faster, cleaner calibration). Next: shadow-mode sidecar
  integration (log rerank scores + would-decisions, serve unchanged) behind
  env flag, then enforce only after live-traffic calibration.

## 11. Rerank-leg gate enforce (2026-10-15): wire + cutoff + E2E

Carries out the §6.4 / §10 "next": the cross-encoder joins the gate
decision at the same post-accumulation gate point. Calibration first,
then wire, then live E2E against a lexical-only control.

### 11.1 Cutoff calibration (per-hit, full corpus)

Harness (gitignored, host-local): `_workspace/rerank_gate_calibration.py`
`score` (per-hit nano-CPU logits over the 50 bake-off top-30 windows;
transcript `_workspace/rerank_gate_scores.json`) + `sweep` (no model).
Rule under test, per hit with notice-OR after:
`keep <=> (rerank >= cutoff) OR (denseTop1 >= 0.6 AND evidence)`;
unscored tail falls back to the lexical rule. Sweep over 40 labeled +
5 noise + 5 vague-valid:

| cutoff | labeled kept-any | in-window targets kept | noise fully emptied | vague kept |
| ------ | ---------------- | ---------------------- | ------------------- | ---------- |
| -2.0 | 40/40 | 24/24 | 4/5 | 4/5 |
| **-1.0** | **40/40** | **24/24** | **5/5** | 3/5 |
| -0.5..1.0 | 38/40 | 24/24 | 5/5 | 3/5 |

- **Shipped cutoff: -1.0** — zero gate damage (the 16 missing targets are
  out of the dense top-30 window at *every* cutoff, a recall gap, not gate
  damage), all 5 noise emptied. Matches the §10 top-1 split independently.
- Cutoffs >= -0.5 fully empty 2 labeled queries (`KIC 관련법 개정`,
  abbr, rerankTop1 -0.83; `해외직구할 때 관세…`, paraphrase, -0.54) —
  the abbr/paraphrase class sets the ceiling, which is why -1.0, not -0.5.
- Noise survivor at -2.0 is `우리 동네 축제 일정` (rerankTop1 -1.36,
  10/30 evidence hits): generic-token evidence is exactly the leak the
  rerank leg closes.

### 11.2 Wire changes (all additive, fail-open)

1. **Sidecar** (`semantic-search/service/app.py`, `reranking.py` untouched):
   `SearchHit` gains `rerankScore: float | None = None`; `search()` scores
   the served window once via `score_rerank_window` (ex-`log_rerank_shadow`,
   same log line) and annotates per hit by chunk id. No filtering —
   §1 annotate-not-filter holds. `RERANK_MODE` values unchanged
   (`off`/`shadow`); scorer-absent windows serve `None`.
2. **Backend types** (`semantic-search.types.ts`): `SemanticSidecarChunk`
   gains `rerankScore?: number | null` (contract spec passes unmodified —
   it pins field-by-field automatically).
3. **Backend config** (`app.config.ts`): `semanticSearch.rerankCutoff:
   number | null` from `SEMANTIC_SEARCH_RERANK_CUTOFF`
   (`parseRerankCutoff`: blank/missing/invalid → null = leg disabled).
4. **Backend gate** (`semantic-search.service.ts`): `keepChunk` =
   rerank-known ? (rerank >= cutoff OR (bypassed AND evidence)) :
   today's lexical rule. Notice-OR preserved (first chunk still decides
   content); null cutoff is byte-identical to the old behavior; the
   query-level bypass override is untouched. Shadow log appends
   `rerankCutoff=` only when active.

### 11.3 Tests

- Backend `semantic-search.service.spec.ts` (+5 in new `rerank-cutoff leg`
  block): high-rerank/no-evidence kept (the `예보법 개정` class),
  evidence-backed/low-rerank dropped (the `오늘 점심 메뉴` class),
  bypass+evidence kept under rejecting rerank, unscored → lexical rule,
  null cutoff ignores scores.
- Sidecar `tests/test_service.py` (+2): annotation attached in shadow,
  `None` while off, scoring failure serves unscored (never 500).
- Suites: semantic-search 337 passed; backend 83 suites / 1214 tests
  passed; `tsc`, `nest build`, backend lint, ruff, comment checker clean.

### 11.4 Live E2E re-measurement (118,331-chunk index)

Sidecar `:8311` (shadow) + backend `:3001`, 14-query matrix (§8 shape),
`enforce` with cutoff `-1` vs lexical-only control (same day/index):

| query | lexical-only | +cutoff -1 |
| ----- | ------------ | ---------- |
| `오늘 점심 메뉴` (noise, fake evidence) | 0/0 | 0/0 |
| `2026 월드컵 우승 전략` (noise) | **1/5** | **0/5** |
| `우리 동네 축제 일정` (noise) | 0/5 | 0/5 |
| `asdfghjkl` (noise) | 0/0 | 0/0 |
| valid x6 (`스토킹처벌법 강화`, `예보법 개정` incl. zero-evidence, `중처법`, `공장에서 일하다…`) | 5/0 each | 5/0 each (identical) |
| vague `돈 관련 법` / `환경 보호` | served | served; `그거 어떻게 되나요` emptied |

- **Meaningful change**: the last fake-evidence clear hit (`월드컵` 1→0)
  is gone; valid serving is bit-identical (no regression, including the
  zero-evidence alias and the colloquial paraphrase classes).
- Residual: 2 noise queries keep weak-only (0/5) rows — clear is empty
  (the engine's answer), weak stays behind the reveal by design.
- Rollout: ship with `SEMANTIC_SEARCH_RERANK_CUTOFF` unset (leg off,
  today's behavior), set `-1` per environment after watching
  `lexical-gate-shadow … rerankCutoff=-1` would-decisions on live traffic.

## 12. Production-readiness close-out (2026-10-15)

Remaining gaps for a safe deploy, all closed without behavior change:

1. **Config-parser coverage**: `parseRerankCutoff` had no direct test
   (operator typo → silent disable is the fail-safe, but it must be
   pinned). New `backend/src/config/app.config.spec.ts` covers
   unset/blank/non-numeric → null and `-1`/`-1.0` parsing.
2. **Operator docs**: `backend/.env.example` now documents the three gate
   vars (all commented, so copying the file changes nothing):
   `SEMANTIC_SEARCH_LEXICAL_GATE`, `SEMANTIC_SEARCH_LEXICAL_BYPASS_SCORE`,
   `SEMANTIC_SEARCH_RERANK_CUTOFF` (recommended `-1`, §11.1).
   `docker-compose.yml` intentionally untouched: env ownership stays with
   the files (same precedent as `UPDATE_CRON`), and both services' code
   defaults keep the legs off.
3. **Timeout headroom**: rerank top-20 CPU ≈ 0.9/1.2 s (scaled from the
   §10 top-30 med/max 1332/1856 ms on M3) + dense ≈ 0.3 s, far under the
   10 s `SEMANTIC_SEARCH_TIMEOUT`. No timeout change needed; prod-CPU
   re-measurement is still advised (limitation carried over).
4. **Cold start**: the nano weights (~600 MB) download once into the
   shared `lawcast_semantic_hf_cache` volume on first shadow boot
   (same mechanism as KURE-v1); no new dependency
   (`sentence-transformers` already required) and no Dockerfile change.

Rollout order (unchanged from §11.4): deploy with the cutoff unset
(leg off, today's behavior) → watch
`lexical-gate-shadow … rerankCutoff=-1` would-decisions on live traffic
→ set `SEMANTIC_SEARCH_RERANK_CUTOFF=-1` in `backend/.env` and
`LAWCAST_SEMANTIC_RERANK_MODE=shadow` in `semantic-search/.env`
together (the leg needs annotated hits to decide on). No commit or
release cut in this session; that follows the AGENTS.md submodule
flow (version bump → PR → merge → tag) on explicit request.

## 13. Unrelated-query full-corpus probe (2026-10-16): is the lexical gate improvable?

Committed harness: `semantic-search/scripts/08_unrelated_probe.py` +
`semantic-search/data/unrelated_queries.jsonl` (40 unrelated in 7 families:
gibberish / english-ood / daily-life / sports-entertainment / foreign /
generic-trap, plus 6 vague-boundary and 8 valid-control). Each query runs
the real 118,711-chunk KURE-v1 index (top-15 window) through dense tiers
and `filter_by_lexical_evidence`; the JSON records per-hit overlaps and
shared tokens so gate variants simulate offline. Combined run with the 40
labeled queries (94 total) reproduces §7: 40/40 labeled kept, 0 damage.

| family | n | clear served | evidence kept | fully emptied |
| ------ | - | ------------ | ------------- | ------------- |
| gibberish + english-ood | 10 | 3 | **0** | 10 |
| daily-life / sports / foreign | 22 | 18 | 19 | 3 |
| generic-trap (synthetic) | 8 | 8 | 8 | 0 |
| valid-control / valid-labeled | 8 / 40 | 8 / 40 | 8 / 40 | 0 damage |

- **Zero-token class is solved**: gibberish and English leak nothing
  through the gate (the 3 clear-served rows have kept=0, so enforce empties
  them). Dense tiers alone serve them — the gate is doing real work here.
- **Residual 21 leaks are genuine single-token overlaps**, not generic-word
  noise: `로또`→복권기금법, `영화`→영화비디오법, `강아지`→동물보호법,
  `우크라이나`→대외무역법… the token really is in the bill. Any token rule
  must keep these.
- **Variants simulated offline** (exact, chunk texts re-tokenized):
  min_shared=2 empties 27/40 but damages 8/40 labeled + 2/8 control
  (rejected, confirms §7); IDF-sum thresholds never beat min1 without
  damage (rare single tokens score high by construction); +44 generic
  stopwords (DF-top + leak-frequency) empty 19/40 with 0/48 damage — but
  all 6 gains are the synthetic generic-trap set, real-category gain 0/21.
- **Decision: do NOT tighten the lexical gate.** It is at its ceiling;
  the residual class is semantic (token present, intent unrelated) and
  belongs to the rerank leg (§11, already wired), not to more stopwords.
  The +44 stopword set is recorded here (not shipped: unproven real-world
  benefit for added stop surface; re-evaluate if shadow logs show
generic-token false-keeps). Corpus DF snapshot method:
  `chunk_tokens` over `artifacts/chunks.jsonl` (N=118,711, vocab 234,986;
  top tokens `있음/법률/이에/것임/있도록…`) — rerun on demand, not stored.

## 14. Combined-gate finalization (2026-10-16): cutoff -1 confirmed on the leak set

Question: does rerank cutoff -1 actually block the §13 residual leaks (the
21-27 Korean unrelated queries the lexical gate must keep), and at what
valid-query cost — measured with the *shipped* backend rule, not the
calibration approximation. New committed harness
`semantic-search/scripts/09_rerank_gate_probe.py` composes on an 08 JSON
document: it scores each stored window with the nano cross-encoder (CPU,
94 windows x 15 pairs in ~59 s) and applies `SemanticSearchService`
verbatim, including the query-level bypass override (`served = bypassed ?
all : gated`, `service.ts:194-195`) that the §11.1 harness did not model.
Input transcript: `/tmp/combined_out.json` (94 queries); output
`/tmp/rerank_gate_out.json` (regenerable, not stored).

| cutoff | unrelated emptied | labeled kept | targets lost | control | vague |
| ------ | ----------------- | ------------ | ------------ | ------- | ----- |
| (lexical only) | 13/40 | 40/40 | 0 | 8/8 | 3/6 |
| -2.0 | 25/40 | 40/40 | 0 | 8/8 | 4/6 |
| -1.5 | 27/40 | 40/40 | 0 | 8/8 | 3/6 |
| **-1.0** | **30/40** | **40/40** | **0** | **8/8** | 3/6 |
| -0.5 | 31/40 | 38/40 | 0 | 7/8 | 3/6 |
| >= 0 | 31-35/40 | 38/40 | 0 | 7/8 | 2/6 |

- **Confirmed: -1.0 is the shipped value.** 18 of the 27 lexical leaks
  newly empty, zero damage on all 48 valid queries (labeled targets lost
  0). -0.5 buys +1 unrelated at the cost of 2 labeled + 1 control — the
  same ceiling §11.1 found on its set, now reproduced on the leak set with
  the exact rule. No code change: the cutoff is operator env, already
  documented as `-1` in `backend/.env.example`.
- **Survivors (10) split three ways**: (a) 1 bypassed
  (`새로운 제도 기반 마련 방안`, top1 exactly 0.600 — ungateable by
  design); (b) 8 generic-phrased queries the model scores clearly
  relevant (rerank +0.6..+4.1: `국가 전략 계획 수립 절차`→4.08) — the
  bills genuinely are about that generic content, so serving them is
  defensible and silencing them needs intent classification, out of scope;
  (c) 1 rescue (`New York subway delay refund`, rerank +0.05 on zero
  evidence — lexical-only would empty it, the leg keeps it). Only (c) is
  mildly wrong, and single-query scale; watch the class in shadow logs
  rather than moving the cutoff.
- **Bypass override shelters almost no noise**: 1/40 unrelated queries
  reach top1 >= 0.6, so the override stays a valid-query protector, not a
  leak vector. Combined rule finalized: bypass → serve ungated; else keep
  <=> rerank >= -1 (scored) else evidence (unscored tail), notice-OR.
  Rollout unchanged (§12): deploy leg-off, watch shadow would-decisions,
  then set both envs together.
