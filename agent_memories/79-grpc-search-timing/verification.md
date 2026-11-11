# Transport-Aware Search Timing

## Audit and changes

SvelteKit still calls the public HTTP backend in development. The backend
already measured both sidecar clients but reported a synthetic HTTP 200
for successful RPCs and mapped RPC errors to HTTP-like status codes in
diagnostics. The frontend rendered every such status as HTTP. The
application error mapping is needed for cap negotiation and keyword
fallback, but it does not represent the sidecar wire outcome.

Each timing attempt now records its actual transport, with HTTP status or
native gRPC code. The UI names HTTP paths versus RPC methods and keeps the
outer HTTP status separate. The waterfall uses the transport-aware name.
Successful calls with the same logical operation and chunk window can be
compared across transports; protocol-specific errors remain separate.
Legacy saved records remain readable without claiming a transport.

The backend passes the UUID and 1-based attempt number by HTTP headers
or gRPC metadata. The sidecar validates both and includes them in completed
search timing logs; the context propagates through worker threads.
Optional embedding/rank wait fields are carried by JSON and Protobuf.
Waits are displayed as measurements within Dense, not summed again or
assigned invented start offsets. Older payloads may omit these fields.
The response header size bound and diagnostic-only SvelteKit scope remain.
Browser-facing API proxy behavior is unchanged.

## Verification

A real Vite development server, the compiled backend search service and
middleware in an isolated Express harness, and a real Python sidecar on
the local 122,624-chunk index completed both HTTP and gRPC Chromium flows.
The browser displayed outer HTTP 200 in both cases, inner HTTP 200 or
gRPC OK (0) as appropriate, and worker waits. Both UI trace IDs matched
sidecar search attempt 2 in the service logs. The two requests are
functional checks, not a performance comparison.

Socket tests cover a gRPC stale-cap retry (OUT_OF_RANGE), native
DEADLINE_EXCEEDED alongside HTTP 200 keyword fallback, zero wait
presence, and malformed correlation metadata. Browser fixtures cover
the transport display and mixed HTTP/gRPC comparison. No deployment was
performed.
