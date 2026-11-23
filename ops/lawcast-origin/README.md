# Authenticated LawCast Service Origin

The public backend and viento.me Bot Fight Mode remain unchanged. The server-only origin `https://lawcast-origin.viento.me/api` terminates TLS in an independent Caddy service and requires a 256-bit random `X-Lawcast-Service-Token` before proxying to loopback NestJS. Caddy strips the credential before the backend. All existing NestJS authorization, PoW and visitor-IP read limits still apply.

## Ownership and exposure

- Caddy 2.11.9 is pinned from the official caddyserver/caddy release and verified against its release checksum manifest. This one process owns TLS issuance and renewal using TLS-ALPN-01; no persistent DNS API credential is installed on the host.
- A dedicated DNS-only A record points to the existing origin IP. Its HTTPS listener is the only service on port 443. The firewall's existing Cloudflare-only HTTP rule remains; one explicit IPv4 TCP 443 rule allows authenticated HTTPS ingress. Existing public HTTP hosts are not exposed directly by this change. No SSH, database, Redis or container port is opened.
- Missing and incorrect credentials return 403 before NestJS. Non-API paths return 404 after authentication. Redirects are rejected by frontend fetches so custom credential headers cannot leak to another origin.
- The systemd service has a dynamic unprivileged user, only CAP_NET_BIND_SERVICE, private runtime/state directories and a private Unix administration socket. Its failure does not restart nginx, Docker or another project.

## Installation

1. Save the original nginx configuration, `/etc/iptables/rules.v4` and `iptables-save` output in the host's root-only operation backup directory. Confirm port 443 is unused.
2. Download `caddy_2.11.9_linux_amd64.tar.gz` and `caddy_2.11.9_checksums.txt` from the official GitHub release, verify SHA512 and install the extracted binary as `/usr/local/bin/lawcast-origin-caddy` (0755, root-owned).
3. Generate `openssl rand -hex 32` into a root-only secret file. Install `/etc/lawcast-origin/service.env` (0600) with `LAWCAST_API_SERVICE_TOKEN=<secret>`. Do not log, commit or return the value.
4. Install Caddyfile and check-env.py at the paths referenced by the service; install the unit in `/etc/systemd/system`. Validate the configuration with the credential environment loaded, but never print the adapted configuration.
5. Add only `-p tcp --dport 443 -m comment --comment lawcast-authenticated-origin -j ACCEPT` to INPUT before HTTP_POLICY, and insert the corresponding line in the existing persistent filter rules. Validate the persistent rules with `iptables-restore --test`; do not overwrite unrelated runtime Docker rules.
6. Enable/start only `lawcast-origin.service`. Check TLS issuance and the original application's health. TLS renews within Caddy; no reminder or external automation is needed.
7. Set server-only Pages bindings `API_SERVICE_URL` and `API_SERVICE_TOKEN` together, preserving every existing encrypted binding. Keep the old API_BASE_URL for explicit rollback. Deploy a frontend with service-origin support only after the backend snapshot release is live.

## Acceptance and rollback

Verify missing/wrong credentials return 403, valid credentials return JSON over verified HTTPS, visitor IP forwarding remains unchanged, the credential is absent from browser responses, and cross-origin redirects are rejected. Re-run a genuine Google live URL test and read all sitemap children.

To roll back routing, remove both service bindings and deploy through the normal frontend release workflow. Only after traffic returns to the public path, stop/disable this independent service, delete its specific INPUT rule and persistent line, and remove its dedicated DNS record. Do not restore an entire saved iptables runtime dump over active Docker state. Preserve certificate state for audit; private keys and tokens remain root/service-only.
