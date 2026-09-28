# Web Push Failure Handling & Cleanup Cron Audit — Bug Findings

Audit scope: (1) whether web push send-failure exception handling matches the browser push providers' specs (FCM, Mozilla autopush, Apple/VAPID), and (2) whether deletion-marked webhooks/subscriptions are actually collected by the cleanup crons. Two bugs found and fixed, with real-path regression tests added.

## Spec baseline (what the providers define)

- **RFC 8030 / web push protocol**: 404 and 410 are the only responses meaning the push subscription itself is invalid/gone; the application server removes the subscription. 429 (with `Retry-After`) and 5xx are transient — retry later, keep the subscription.
- **FCM error codes** (firebase.google.com/docs/cloud-messaging/error-codes): `UNREGISTERED` (HTTP 404) means the token is no longer valid and must be replaced — delete. 429 = quota, retry.
- **Mozilla autopush** (mozilla-services.github.io/autopush-rs/http.html): 404 "Push subscription is invalid", 410 "Push subscription is no longer available"; other errors carry `errno` values indicating whether retries are available.
- Industry reference: pushpad "Web Push errors explained (with HTTP status codes)" — 404/410 remove, 429/500 retry.

## Bug 1 (**HIGH**): transient failures permanently deleted valid subscriptions

**Where**: `backend/src/modules/notification/web-push-subscription.service.ts` (`markFailure`, `cleanupInactiveSubscriptions`).

**Root cause**: `markFailure` deactivated a subscription when `failureCount >= 5` regardless of failure class, and `cleanupInactiveSubscriptions` hard-deleted with `(is_active = 0 AND updated_at < cutoff) OR failure_count >= 5` — no retention for the second clause. So repeated **transient** failures (429/5xx/network) invalidated *and immediately hard-deleted* a subscription the providers still consider valid. During a push-service outage spanning 5 dispatch cycles, every subscription would be destroyed (mass data loss), and the row was gone before `createOrReactivate` could heal it.

**Fix**: only the explicit `deactivate` flag (set exclusively on 404/410 in `web-push-notification.service.ts` `sendSingleWithRetry`) marks a subscription inactive; `failureCount`/`lastFailureReason` remain for observability only. `cleanupInactiveSubscriptions` now deletes only `is_active = 0 AND updated_at < cutoff` (the hard-delete side of 404/410 marking), and the discussion-binding sweep matches that exact condition. Removed the now-dead `webPushFailureDeactivationThreshold`.

**Spec-conformant classification after fix** (verified by tests):
- 404/410 → no retry, deactivate immediately (FCM UNREGISTERED / autopush 404/410 semantics).
- 429 → in-flight retry honoring `Retry-After` (seconds or HTTP-date), keep subscription.
- 5xx (500/502/503/504) + network codes → in-flight retry with backoff, keep subscription.
- 400/401/403/413 → no retry, no deactivation (request/config errors, not subscription invalidity).

## Bug 2 (**MEDIUM**): webhook cleanup cron gate measured a different window than its delete query

**Where**: `backend/src/modules/webhook/webhook-cleanup.service.ts` (`intelligentWebhookCleanup` step 1) vs `backend/src/modules/webhook/webhook.service.ts` (`getDetailedStats`).

**Root cause**: step 1 ("clean up old inactive webhooks (14+ days)") was gated on `stats.oldInactive > 0`, but `getDetailedStats` computes `oldInactive` with a **30-day** window while `cleanupOldInactiveWebhooks(14)` deletes at **14 days**. With typical high efficiency (>= 70%), steps 2/3 never run, so webhooks deactivated via `WebhookService.remove()` (the deletion-marking write point used by `notification-batch.service.ts` on permanent Discord failures) were only collected once some row crossed 30 days — ~2x the documented retention.

**Fix**: gate step 1 on `stats.inactive > 0`; the cleanup query itself applies the precise 14-day condition. Regression test: `webhook-cleanup.service.spec.ts` ("collects deletion-marked webhooks even when none pass the 30-day old-inactive counter").

## Test-path gap found and closed

All prior cleanup tests mocked repositories/query builders, so no test exercised the real SQL against real columns. Added real-sqlite regression specs (run under `npm test`, not e2e-only — see the `source-deletion-detection.e2e-spec.ts` pitfall note):

- `backend/src/modules/webhook/webhook-cleanup-data-flow.spec.ts`: `remove()` marking → `intelligentWebhookCleanup` collection; retained at 5 days, collected at 20 days, active rows untouched (high-efficiency scenario that reproduces Bug 2).
- `backend/src/modules/notification/web-push-cleanup-data-flow.spec.ts`: 404/410 marking → `cleanupInactiveSubscriptions` collection with bindings after retention (kept within retention); transient-only failures (failureCount 5) never collected (reproduces Bug 1).

Both were verified to **fail against the pre-patch services** and pass after.

## Schema/casting pitfalls for these tables

- `webhooks` uses **camelCase** DB columns (`isActive`, `updatedAt`) — created by `migrations/202604170001-initial-schema.migration.ts` matching the entity's default naming. Raw SQL/backdating against it must use `updatedAt`, not `updated_at`.
- `web_push_subscriptions` / `discussion_web_push_bindings` use snake_case via explicit `@Column({ name })` mappings; `cleanupInactiveSubscriptions` raw SQL (`is_active`, `updated_at`, `failure_count`) matches those names.
- TypeORM sqlite persists and binds `Date` values uniformly as `DateUtils.mixedDateToUtcDatetimeString` ("YYYY-MM-DD HH:MM:SS.mmm" from **UTC** components), so raw `UPDATE ... SET updated_at = ?` backdating in tests must use the same UTC string format (`date.toISOString().replace('T',' ').replace('Z','')`).
- `sendSingleWithRetry` builds the failure reason via `error instanceof Error ? error.message : String(error)`; real `web-push` errors are `WebPushError extends Error`, but plain-object rejections degrade to "[object Object]" — use Error-based mocks in tests.

## Not changed (accepted behavior / open minor gaps)

- 404/410-deactivated rows are soft-removed immediately (excluded from `findAllActive`) and hard-deleted after the 14-day retention window — intentional retention policy.
- `isRetryableError` network-code list covers ETIMEDOUT/ECONNRESET/ECONNREFUSED/EAI_AGAIN; `ENOTFOUND`/`EPIPE` are treated as non-retryable (only skipped in-flight retry; the subscription is still kept).
- `markSuccess` sets `isActive: true`, which can resurrect a row deactivated by a concurrent 410 — benign because it only happens after a genuinely successful send.
- Discord webhook side (`NotificationService.shouldDeleteWebhook`) is spec-conformant already: 401/403/404/10015 (Unknown Webhook) delete, 429/5xx keep.
