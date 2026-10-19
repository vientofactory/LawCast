# GTM Consent Diagnostic Investigation

## Conclusion

Investigated on 2026-10-18 JST, using the user's current Chrome GTM tab, frontend commit history, production HTML, Google documentation, and Tag Assistant. The warning **does not mean analytics consent is always denied**. It is Google's advertising-oriented diagnostic for globally denied `ad_user_data`, which matches LawCast's current analytics-only consent policy.

No source code, consent policy, GTM tag settings, published versions, account access, or Cloudflare rules were changed during this investigation. Tag Assistant was switched from workspace preview to the Live environment solely for browser debugging.

## Exact dashboard findings

The container showed two items:

- Urgent: zero consent rate in some regions. Its description mentions all signals denied even outside the EEA and impact on advertising measurement/personalization.
- Recommendation: add another administrator. This is account recovery redundancy, not an event collection error; no administrator was added.

Google's [Tag Diagnostics reference](https://support.google.com/tagmanager/answer/14681508?hl=en) explicitly defines the regional zero-percent warning as always sending `ad_user_data: denied` outside the EEA. This distinction is decisive: `ad_user_data` is not `analytics_storage`.

## Recent frontend commits

- `8a17eeb`, PR #154, 2026-10-16: initial consent-gated GTM integration and build-time container ID.
- `bc80283`, PR #156, 2026-10-16: switched from blocking the container itself to loading it with denied defaults. The earlier consent helpers queued Arrays instead of Google command Arguments objects.
- `457ce0e`, PR #159, 2026-10-16: moved snippet to the SSR head, but used `/gtag/js?id=GTM-...` and `gtag(config, GTM-...)`, mixing the Google tag loader with a Tag Manager container ID. Its runtime consent code still queued Arrays.
- `583df08`, PR #160, 2026-10-18 03:42 JST, frontend v1.19.4: restored the proper `gtm.js?id=GTM-...` container bootstrap, uses Arguments objects, restores accepted visitors before GTM, and updates analytics consent explicitly rather than sending a second default. **It intentionally keeps advertising denied even when analytics is accepted.** This is the direct explanation for the diagnostic.

Relevant current source:

- `frontend/src/lib/utils/gtm-bootstrap.ts:9`: denied defaults, browser-local stored-choice restoration, then `gtm.js` bootstrap. Only `analytics_storage` changes to granted.
- `frontend/src/lib/utils/consent.ts:76`: updates analytics according to acceptance and always leaves `ad_storage`, `ad_user_data`, and `ad_personalization` denied.
- `frontend/src/lib/utils/gtm.ts:36`: queues `virtual_pageview` only for accepted visitors.
- `frontend/src/routes/+layout.svelte:27`: initial/SPA navigation invokes the helper.
- `frontend/src/lib/components/CookieConsentBanner.svelte:62`: choosing accept applies an update and records the current page once when newly accepted.
- `frontend/e2e/analytics-consent.spec.ts`: five isolated regression cases cover denied/declined, first acceptance + SPA, return visits, withdrawal, and blocked storage. These tests mock Google responses, so source-level tests alone cannot prove actual GTM tag execution. They were inspected but not rerun in this read-only diagnosis; the runtime validation below exercises real tags.

## Published GTM configuration inspected

- Latest and Live container version is **5**, named `Block data transmission without consent`, published 2026-10-18.
- Version 4 is `Fix GA4 virtual page views`.
- Workspace showed **0 pending changes** before inspection.
- Google Analytics initialization tag targets the configured GA4 destination and fires on Initialization - All Pages. Its configuration has `send_page_view=false`, avoiding an automatic initial page view on top of the custom event.
- GA4 Event tag uses event name `page_view` and trigger `CE - virtual_pageview`. Event parameters include data-layer page_location/page_title and built-in Page Path.
- Initialization tag's built-in consent checks list all four categories; additional consent checks were not configured on that tag. A built-in advertising category being denied does not by itself prove the analytics event is blocked.

## Real browser verification

Connected the real deployed frontend to Tag Assistant, first in workspace preview and then explicitly to **Live** via its environment selector. The browser already had an accepted analytics preference; it was not changed.

Observed:

1. Default consent event precedes GTM initialization.
2. Returning-visitor update precedes the first page view.
3. First `virtual_pageview`: Google Analytics initialization tag fired once; GA4 page_view event tag fired once. Tag Assistant's sent-hits pane listed a page view to the GA4 destination.
4. SPA navigation from `/` to `/notices` generated exactly one additional `virtual_pageview` in the observed sequence. Its data-layer pane contained `page_path: "/notices"`, `page_location: "https://law.viento.me/notices"`, and the correct notices title. Its sent-hits pane listed a page view.
5. After switching to **Live** and reloading, Tag Assistant's summary explicitly displayed the Live environment. A fresh page-view event again showed `analytics_storage` updated from denied to **granted**, while all three advertising categories stayed **denied**. The summary listed page views and a user_engagement hit.
6. Tag Assistant console indicator remained **0** in the observed session.

This verifies frontend execution, consent interpretation, and the outgoing-hit report. It does not measure all-user consent rates or prove final GA4 report ingestion, which can be delayed or filtered.

## Cloudflare relationship

A direct public GET to the home page returned `CF-Cache-Status: EXPIRED` and `Cache-Control: max-age=0, s-maxage=120, public`. Its actual inline bootstrap matched the latest source: proper GTM loader, Arguments commands, and analytics-only grants.

The choice is read from **each visitor's browser localStorage when the script runs**. It is not interpolated into server-generated HTML, so sharing identical HTML does not share a previous visitor's consent. Current evidence does not implicate the recently applied Cloudflare rules in the zero-percent advertising diagnostic. Historical long-lived browser HTML may still be held by some returning clients; that is a separate limitation documented in [the cache review](../47-cloudflare-page-cache/cache-review-and-validation.md).

## Recommended disposition

- Keep advertising consent denied while the banner only requests analytics consent. Do not grant advertising categories merely to remove this warning.
- Treat this diagnostic as an expected consequence of the current policy, with live GA4 behavior verified separately. It is not necessarily a transient warning that will disappear after waiting, because the denied advertising signal remains intentional.
- If advertising measurement or personalization becomes an actual product requirement, first define a separate user-facing choice and its corresponding consent updates. That would be a new policy/product change, not a bug fix for this diagnostic.
- The administrator recommendation can be addressed separately by the account owner if desired.

## Evidence sources

- [Google Tag Diagnostics](https://support.google.com/tagmanager/answer/14681508?hl=en): defines the zero-percent advertising signal diagnostic.
- [Google Consent Mode setup](https://developers.google.com/tag-platform/security/guides/consent): distinct analytics/advertising parameters and update ordering.
- [Consent Mode troubleshooting](https://support.google.com/tagmanager/answer/14522438?hl=en): use Tag Assistant to distinguish default and update behavior.
- Screenshot of the Live page-view consent state saved as a chat artifact, without recording preview-authentication URLs in repository notes.
