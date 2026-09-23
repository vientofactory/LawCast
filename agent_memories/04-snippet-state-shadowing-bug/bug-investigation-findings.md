# Svelte 5 Snippet/State Name Collision Breaks `bind:value` in NewThreadModal

## Symptom

**HIGH** — In the frontend "새 토론 주제 개설" modal (`frontend/src/lib/components/discussions/NewThreadModal.svelte`), submitting with a valid 토론 주제 (title) still showed the client-side validation error `토론 주제를 2자 이상 입력해주세요.` The thread could never be created from the UI.

Only the **title** field was affected. 비밀번호 / 첫 발언 내용 / 닉네임 bindings worked normally.

## Root Cause

**The component declared `let title = $state('')` while also passing `{#snippet title()}` to `ModalShell`.** The snippet name and the state name collided.

- `ModalShell.svelte` receives header content via snippets named `icon`, `title`, `subtitle`, so the snippet name is fixed by the prop contract and cannot be renamed freely.
- Snippet declarations are compiled into a `const <name>` inside a block scope that **also encloses the `children` closure** (the default slot containing the form).

Compiled output of the original component (Svelte 5.41, `compile()` from `frontend/node_modules/svelte/compiler`):

```js
export default function NewThreadModal($$anchor) {
	let title = $.state('');          // instance scope — what handleSubmit reads
	function handleSubmit() {
		if (!$.get(title).trim() ...) { /* validation reads the real state */ }
	}
	{
		const title = ($$anchor) => { /* ... */ };   // snippet — SHADOWS the state
		ModalShell($$anchor, {
			title,                                    // correct: passes the snippet
			children: ($$anchor) => {
				// 'title' resolves to the snippet function, not the state:
				$.bind_value(input, () => $.get(title), ($$value) => $.set(title, $$value));
			}
		});
	}
}
```

Runtime consequences:

1. `$.get(snippetFn)` reads `fn.v` -> `undefined`, so the binding never reflects typed text back.
2. `$.set(snippetFn, value)` reaches `internal_set()`, which calls `source.equals(value)` -> **`TypeError: source.equals is not a function`** on every keystroke (thrown as an unhandled rejection inside the async `input` listener).
3. The `title` state therefore stays `''` forever, while `handleSubmit` validates the real state -> the error message appeared no matter what the user typed.

No compiler warning or type error was emitted — `npm run lint` and `npm run check` both passed with the bug present.

## Evidence Trail

- Symptom string: `frontend/src/lib/components/discussions/NewThreadModal.svelte` (line 62 of the original file, inside `handleSubmit`)
- Collision sources: `let title = $state('')` (original line 29) vs `{#snippet title()}` (original line 94)
- Compiled proof: `compile(source, { generate: 'client' })` output — `bind_value(input, ...)` closed over the snippet `const title` (block opened at generated line 83, snippet at line 99, binding at line 262)
- Runtime failure point: `frontend/node_modules/svelte/src/internal/client/reactivity/sources.js` -> `internal_set()` (`if (!source.equals(value))`)

## Fix Applied

Renamed the state variable `title` -> `threadTitle` in `NewThreadModal.svelte` (declaration, `handleClose`, `handleSubmit` validation/payload, `bind:value`). The snippet stays named `title` because it is the `ModalShell` prop key. A comment above the declaration documents the constraint.

Verified by recompiling the component: `$.bind_value(input, () => $.get(threadTitle), ($$value) => $.set(threadTitle, $$value))` — binding and validation now reference the same state. `cd frontend && npm run lint && npm run check` -> 0 errors.

Regression coverage: `frontend/e2e/discussions.spec.ts` now contains two mock-gated tests — "new thread modal rejects an empty or whitespace-only title" (validation still works, no POST sent) and "creates a new thread with the entered title" (asserts no error banner, navigation to thread detail, and the trimmed title in the POST payload). The second test was verified to FAIL when the `threadTitle -> title` rename is reverted, so it genuinely guards this bug. Run with `DIFFCHAIN_UI_MOCK=1 npm run test:e2e -- e2e/discussions.spec.ts` (always pass `--config` via `npm run test:e2e`; bare `npx playwright test` picks up no config and fails with `Cannot navigate to invalid URL`).

## Prevention Notes for Other Agents

- **CRITICAL**: In any component that passes snippets to `ModalShell` (`icon`, `title`, `subtitle`), never name a `$state`/`let` variable the same as a snippet. The snippet wins inside the default-slot markup, silently breaking `bind:value`.
- Audited all snippet usage in `frontend/src`: only `NewThreadModal.svelte` had this collision (`FullUnsubscribeConfirmModal`, `DiscussionPushConsentModal`, `CommentActionModal` declare `title` snippets but no `title` state).
- To confirm a fix without running the app, compile the suspect component with `svelte/compiler` and check that `$.bind_value(...)` references the intended identifier.
- This appears to be a Svelte compiler codegen weakness (identifier not renamed on shadow) — worth checking upstream `sveltejs/svelte` issues before assuming newer versions fix it.
