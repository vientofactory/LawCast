# Common notifications

## Design and lifetime

The existing `Alert` was inline, defaulted to no expiry, only timed success messages, and used an untracked delayed dismiss callback. Discussion, webhook, push and export feedback each implemented separate banners/timers. These transient messages now use one notification center and presentation.

- `frontend/src/lib/utils/notifications.ts` owns a per-layout center created with Svelte context, not a shared SSR singleton. Each push receives a distinct ID, including identical messages. Removing an ID calls its dismiss callback at most once. Owner teardown removes entries silently.
- `NotificationViewport.svelte` displays at most three FIFO notifications per scope. Excess entries wait without running timers. The fixed lower-right stack fits mobile gutters, safe areas, visual-viewport keyboard inset and the existing consent-banner height.
- `NotificationItem.svelte` uses theme-neutral elevated surfaces with semantic icons/borders and Korean type labels. Success/info/warning/error expire after 5/6/7/8 seconds. Hover, focus, background tabs and inert modal backgrounds pause the remaining lifetime. Every item has a 44px minimum close target; actions retain keyboard access, and keyboard dismissal returns focus to the next item or its connected origin. Reduced-motion settings suppress entrance/exit motion.
- `Alert.svelte` is a declarative compatibility adapter: it registers once per message state, renders no inline banner, removes its registration on owner destruction, and supports refresh/custom actions and optional rich content. `autoHide={false}` retains an explicit X rather than an undismissable message. Its default is timed for every type. New event-driven callers can push directly into the center.
- The root layout hosts page notifications. `ModalShell` supplies a local scope and host within its existing focus trap; it does not exempt unrelated DOM from inertness or break native modal isolation. Alerts determine scope from their rendered DOM anchor, including snippets/lazy forms.

## Usage

```svelte
<script lang="ts">
	import Alert from '$lib/components/Alert.svelte';
	import { useNotifications } from '$lib/utils/notifications';
	const notifications = useNotifications();
	let error = $state('');
	function saved() {
		notifications.push({ type: 'success', message: '저장했습니다.' });
	}
</script>
{#if error}
	<Alert type="error" message={error} onDismiss={() => (error = '')} />
{/if}
```

Use the declarative adapter inside a modal so the local DOM scope is retained. Keep retry/validation source state separate from notification visibility where it also governs recovery controls. Do not store callbacks or notifications in an SSR module-global writable.

## Migration inventory

Transient feedback migrated:
- Existing semantic-search `Alert` and its former inline test wrapper.
- Discussion list/thread success and error banners; independent success timers removed.
- New-thread, comment-action and reply-form validation/mutation errors.
- Quote-push consent feedback and webhook/web-push registration/unsubscribe results.
- Statistics export errors and archive ZIP export errors.
- Timeline comparison and load-more operation warnings.
- PWA installation failure feedback.

Intentionally retained as contextual UI, not ephemeral notifications:
- Rate-limit and semantic-unavailable blocking overlays, their countdown/recovery actions.
- Initial history/image loading failure states with persistent retry buttons.
- Source-deletion/capture/provenance diagnostics, urgent site announcements and service-health diagnostics.
- Search fallback/weak-result disclosures, digest range indicators and statistical interpretation notes.
- Field-specific validation hints, permission/unsupported-browser explanations and PoW progress.

These explain the current data or recovery path; moving them into disappearing toasts would leave misleading content or remove the only recovery affordance. Their existing semantic meaning, controls and placement remain unchanged.

## Verification

`playwright.notifications.config.ts` isolates Chromium, Firefox, WebKit and an iPhone-emulated touch project. The `/notification-test` harness returns 404 unless the private `E2E_NOTIFICATIONS=1` flag is explicitly enabled. Default/integration discovery excludes this specialized suite. It tests actual shared components and a real webhook form, rather than injecting hand-built notification DOM.

Coverage includes 320/820/1440px light/dark stacks, theme changes, axe, queued lifetime, independent severity durations, hover/focus pause, inert background pause, actions, manual dismissal/focus, modal scope, repeated validation, touch/reduced motion and navigation cleanup. WebKit pointer clicks may not focus buttons: focus-return tests explicitly invoke the origin via keyboard rather than assuming Chromium behavior. Initial failures also exposed an ambiguous webhook accessible-label selector and a project grep matching its own filename; the dedicated selectors/grep now target the intended controls/test title.

Evidence and task-start rollback snapshots: `/private/tmp/lawcast-notifications/VERIFICATION.txt`.

The PWA regression exposed a genuine pointer obstruction: retaining an installation-offer panel after its one-shot prompt failed left its old dismissal action underneath the error toast. Failure now removes that obsolete offer and shows only the shared error notification. A live offer reserves its measured bottom space for page notifications (including consent/banner position updates); disposal releases the reservation. The three-engine suite pins nonoverlapping rectangles and dismissal cleanup. The real-worker PWA error test follows the new notification close action instead of targeting the removed panel.

Final checks: 40 notification cases passed across three desktop engines and touch emulation, 42 existing Chromium discussion/webhook/screenshot cases passed, and the isolated real-worker PWA error case passed. Formatting, ESLint, Svelte check (zero errors/warnings), guideline checks and the final Cloudflare production build passed. Independent-copy rollback restores 20 original hashes/removes 7 new files; all 27 active source/test/config hashes remain modified.

## CI follow-up: notification wrapper text

PR 184's first `web-vitals` run (42007718684) failed only the desktop/mobile consent-banner/modal regression. It compared the entire `discussion-new-thread-error` wrapper with the old message-only string. The shared notification correctly adds the severity label `오류`, so the observed text was `오류 토론 주제를 2자 이상 입력해주세요.`. The unchanged test reproduced both failures locally.

`e2e/web-vitals.spec.ts` now scopes the notification to its owning modal, verifies the alert role and exact message leaf, clicks the accessible close button and verifies that the notification disappears while the modal and consent banner remain visible. It does not remove the label or loosen the expected message. The full production desktop/mobile vitals suite passes all 62 cases locally. Evidence and independent test-copy rollback are in `/private/tmp/lawcast-ci-fix/VERIFICATION.txt`.

The next local CI stage exposed four additional fixture failures in `open-layout.spec.ts`: mobile touch cases were being executed by the desktop-only base project, so `(pointer: coarse)` was false before any interaction. The cross-engine theme config already supplied touch contexts, but the new CI invocation used the base config over the entire spec. `playwright.open-layout.config.ts` now keeps 127 desktop cases in `open-layout` and moves all four unchanged mobile touch cases into `open-layout-touch` using the Pixel 7 descriptor. Discovery remains exactly 131 tests; nothing is skipped and real trusted-touch/contrast assertions remain intact. All four pass with the corrected fixture.

The expanded job also needed timing headroom: one remote run spent 4m18s installing Chromium, while the local 131-case layout stage took roughly nine minutes. The existing 15-minute whole-job cap left little room for the other regression stages, so the workflow now uses a bounded 25-minute cap. Individual test timeouts, assertions, retry policy and test count are unchanged. This is an execution-budget safeguard, not a way to bypass failing checks.

Local validation must also remain serialized/isolated: two ancillary full-suite attempts lost their Node server after generated client/server assets disappeared or changed (`ENOENT` / `ERR_MODULE_NOT_FOUND`, followed by connection-refused failures). Shared build manifests/output were not immutable; the exact writer was not established. A separate checkout at the exact signed commit, sharing only installed dependencies, passed the complete 15-page narrow-screen audit plus all four touch cases (5 passed). Treat shared-output failures as invalid local environment results, keep sync/typecheck/build sequential, and use an isolated checkout when other work may regenerate outputs; do not alter application code or retry policy to hide them.

Final remote verification: signed fixes `5423770`, `ddbaad6` and `b0d51f5` were pushed to PR 184 without merging. [CI run 42012241954](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42012241954) passed every step in 13m59s: 48 revision/navigation cases, 62 production vitals cases, all 131 layout/touch cases and 16 SSR consumer cases. GitGuardian and the head commit's GitHub signature verification also passed. The frontend checkout remains clean on `codex/common-notifications`; independent rollback restores all three task-start source hashes without changing the active fixes.


## PR 184 premerge review follow-up (2026-11-06)

The review exposed a discovery gap: the general Playwright configs found the new screenshot touch cases in Desktop Chrome, while the dedicated screenshot config already assigned touch contexts. Both general configs now partition these cases into a real Pixel 7 project without changing discovery count. Chromium serializes `pan-x pan-y pinch-zoom` as the equivalent `manipulation`; the shared assertion accepts these two equivalent values while retaining real taps, zoom, scrolling and viewport-fit checks.

A separate `shared-ui` CI matrix runs the notification, screenshot-modal and theme-states configurations, including Firefox/WebKit and touch contexts. It uses independent jobs rather than extending the original 25-minute Chromium job. Browser dependencies still install normally, failed suites remain failures, and failure screenshots/traces are retained for seven days.

`FormFeedback.svelte` separates persistent form-error descriptions from expiring/dismissible notifications. New-thread, comment-action and reply validation identify the failing field with `aria-invalid` and `aria-describedby`; changing an unrelated nickname does not clear another field's error. Retrying the same invalid submission can reannounce the toast without removing the persistent description. Closing/resetting the form removes both. Webhook URL hints now have the same explicit input association. Notification severity colors moved into light/dark semantic status tokens without changing their values.

Verification artifacts are under `/private/tmp/lawcast-pr184-followup/`; final commands and baseline/modified/independent-copy rollback evidence are recorded in `VERIFICATION.txt`. The frontend stays at the unreleased v1.28.0. PR 184 must remain open and unmerged.

Final follow-up evidence: signed commit `dadb7a6` is GitHub-verified and pushed to PR 184. [CI run 42112912434](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42112912434) passed the existing 336 Chromium regressions plus 147 shared-UI cases (53 screenshot, 46 notification, 48 theme); GitGuardian passed. Local default screenshot/discussion regressions passed all 39 cases, all three dedicated suites passed, and mobile light/dark persistent-error captures were opened and inspected. The source checkout is clean on `codex/common-notifications`; root notes/pointer remain uncommitted. PR remains OPEN with auto-merge disabled; no merge, release or deployment occurred. Independent-copy rollback restored 13 original files and removed the new component, matching every original hash while active modified hashes stayed intact.
