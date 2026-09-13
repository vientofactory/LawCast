# Bug Investigation: Quote-Notification Modal & Cloudflare IP Forwarding

## BUG #1: Quote-Notification Button Does Not Open Modal

### Evidence Path
1. **Button Definition** → [frontend/src/lib/components/discussions/ThreadDetailView.svelte:114](frontend/src/lib/components/discussions/ThreadDetailView.svelte#L114)
   - Button with id `discussion-quote-push-settings` calls `onOpenQuotePushConsent?.()`
   - Receives `onOpenQuotePushConsent` prop (line 32)

2. **Function Pass-down** → [frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte:534](frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte#L534)
   - Passes `onOpenQuotePushConsent={openQuotePushConsent}` to ThreadDetailView

3. **Handler Implementation** → [frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte:104](frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte#L104)
   ```
   async function openQuotePushConsent(): Promise<void> {
     if (!canPromptForQuotePush()) return;  // ← EARLY EXIT HERE
     if (typeof localStorage !== 'undefined') {
       localStorage.removeItem(quotePushDismissalKey);
     }
     await ensureQuotePushConsentModal();
     isQuotePushConsentOpen = true;
   }
   ```

4. **Gating Logic** → [frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte:80](frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte#L80)
   ```
   function canPromptForQuotePush(): boolean {
     return (
       typeof window !== 'undefined' &&
       isWebPushAvailableByServer &&              // ← Could be false
       'serviceWorker' in navigator &&
       'PushManager' in window &&
       'Notification' in window &&
       Notification.permission !== 'denied' &&   // ← Could be 'denied'
       localStorage.getItem(quotePushDismissalKey) !== '1'
     );
   }
   ```

5. **Web Push Config Fetch** → [frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte:130](frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte#L130)
   ```
   onMount(async () => {
     try {
       const config = await apiClient.getWebPushPublicConfig();
       isWebPushAvailableByServer = config.enabled && !!config.publicKey;
     } catch {
       isWebPushAvailableByServer = false;
     }
   ```

6. **Modal Rendering** → [frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte:577](frontend/src/routes/notices/[num]/discussions/[threadId]/+page.svelte#L577)
   ```
   {#if DiscussionPushConsentModalComponent}
     <svelte:component
       this={DiscussionPushConsentModalComponent}
       isOpen={isQuotePushConsentOpen}  // ← Never becomes true if gating fails
   ```

### Root Causes
1. **Most likely**: `canPromptForQuotePush()` returns false because:
   - `isWebPushAvailableByServer = false` (API config fetch failed or server has it disabled)
   - OR `Notification.permission === 'denied'` (user denied permissions)
   - OR `localStorage[quotePushDismissalKey] === '1'` (user dismissed, even though button click tries to clear it)

2. **Secondary**: Race condition - localStorage.removeItem() at line 107 executes but localStorage check at line 90 already evaluated as '1'

3. **Tertiary**: Component not loaded - `ensureQuotePushConsentModal()` might fail silently

### Recent Changes Impact
- No recent changes to modal wiring visible, but if web push config endpoint recently disabled or changed, this would break

---

## BUG #2: Cloudflare Pages SSR Records Wrong IP Despite Header Forwarding

### Evidence Path
1. **Frontend Hook Implementation** → [frontend/src/hooks.server.ts:11](frontend/src/hooks.server.ts#L11)
   ```typescript
   const clientIp = event.request.headers.get('cf-connecting-ip');
   if (!clientIp) {
     return fetch(request);
   }
   const headers = new Headers(request.headers);
   headers.set('cf-connecting-ip', clientIp);
   return fetch(new Request(request, { headers }));
   ```

2. **Adapter Configuration** → [frontend/svelte.config.js:1](frontend/svelte.config.js#L1)
   - Uses `@sveltejs/adapter-cloudflare` (version ^7.2.9 from package.json)

3. **Backend IP Extraction** → [backend/src/modules/discussions/utils/ip-masking.util.ts:12](backend/src/modules/discussions/utils/ip-masking.util.ts#L12)
   ```typescript
   static extractClientIp(req: Request): string {
     const cfIp = req.headers['cf-connecting-ip'];  // ← Expects this
     if (typeof cfIp === 'string' && cfIp.trim()) {
       return this.cleanIp(cfIp.trim());
     }
     // Falls back to x-forwarded-for, x-real-ip, req.ip, req.socket.remoteAddress
   ```

4. **Documentation Note** → [backend/README.md:60](backend/README.md#L60)
   > "프록시 환경에서는 신뢰할 수 있는 `cf-connecting-ip`, `x-forwarded-for`, `x-real-ip` 설정이 필요합니다."

### Root Causes
1. **Incorrect Cloudflare Pages Context**: 
   - `event.request.headers.get('cf-connecting-ip')` reads FROM the Cloudflare edge request
   - In Pages SSR, this is the request between browser → CF edge, not browser → origin
   - Result: Gets CF edge IP instead of true client IP, then passes it downstream

2. **Missing Cloudflare Bindings**:
   - Cloudflare adapter provides `event.platform.cf.request` or `event.clientAddress`
   - Current code ignores these and tries to parse headers instead

3. **Adapter Behavior**:
   - `@sveltejs/adapter-cloudflare` wraps requests; true client IP in `event.platform?.cf?.request?.headers['cf-connecting-ip']`
   - OR available via newer `event.clientAddress` in Pages Platform

### Factual Issue
Backend receives Cloudflare's edge IP in the `cf-connecting-ip` header because frontend is extracting and forwarding the edge IP, not the true client IP from the correct Cloudflare API.

---

## Minimal Fixes

### Fix #1: Quote-Notification Modal
**Root:** `canPromptForQuotePush()` gates opening due to one condition failing

**Minimal fix options:**
- Option A: Check & log each condition in `canPromptForQuotePush()` to identify which fails
- Option B: Remove localStorage gating on button click (just prompt regardless)
- Option C: Make modal open directly without gating (ignore Notification.permission check)

### Fix #2: Cloudflare IP Forwarding  
**Root:** Frontend reads CF edge IP instead of true client IP

**Minimal fix:**
```typescript
// frontend/src/hooks.server.ts
export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
  const requestUrl = new URL(request.url);
  if (requestUrl.origin !== event.url.origin || !requestUrl.pathname.startsWith(API_PATH_PREFIX)) {
    return fetch(request);
  }

  // Fix: Get true client IP from Cloudflare Platform
  const clientIp = event.platform?.cf?.request?.headers?.get?.('cf-connecting-ip') 
                || event.clientAddress
                || event.request.headers.get('cf-connecting-ip');
  
  if (!clientIp) {
    return fetch(request);
  }

  const headers = new Headers(request.headers);
  headers.set('cf-connecting-ip', clientIp);

  return fetch(new Request(request, { headers }));
};
```

OR add to wrangler.jsonc for better routing:
```json
{
  "env": {
    "production": {
      "upstream": "https://your-backend.com",
      "routes": [
        { "pattern": "/api/*", "zone_name": "your.domain.com" }
      ]
    }
  }
}
```
