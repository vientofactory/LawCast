# Search Timing Hydration Regressions

The history test treated an SSR panel as proof that the client had mounted
and persisted its record. Playwright's baseline action log shows the error
search navigating to a new document, then repeatedly failing to find the
first trace ID in the history selector. The dock now restores session state
and saves the current SSR timing before it enables history controls. Later
client navigations use the same deduplication and retention function.

The light/dark test can flip the system media query after the inline paint
script runs but before the client installs its media query listener. The
old client initialized from the stale HTML data attribute. It now reads the
current system setting when no explicit preference exists. Manual toggles
use the live theme store; the saved preference still wins at startup.

Both tests hold the client theme module until the SSR assertions complete,
then release it. The history test checks that the first trace was persisted
before the second search. The narrow-layout test switches the system theme
while the module is held and checks that the system listener works after
mount. Neither case relies on a sleep. Both new regression assertions fail
on the restored runtime; the previous transport/status and comparison
tests still pass on that rollback.
