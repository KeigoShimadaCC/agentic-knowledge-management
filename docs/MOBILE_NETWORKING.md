# Mobile Networking

> Network profiles, Docker Compose exposure rules, and iOS App Transport Security strategy for the KnowledgeOS iPhone client. Companion docs: [`MOBILE_APP.md`](./MOBILE_APP.md), [`MOBILE_API_CONTRACT.md`](./MOBILE_API_CONTRACT.md).

---

## 1. The three profiles

The iOS app must support three API base URL profiles. The user picks one in the Connect screen and the choice is persisted per-install.

| Profile | Base URL | When to use |
|---|---|---|
| **Simulator** | `http://127.0.0.1:8001` | iOS Simulator running on the same Mac as the Docker stack. Loopback bypasses ATS HTTP rules naturally. |
| **LAN (Same-Wi-Fi)** | `http://<mac-lan-ip>:8001` | Physical iPhone on the same Wi-Fi as the Mac. Requires the mobile Compose override (§3) and a narrow ATS exception (§5). |
| **Tailscale** | `http://<mac-tailnet-name>:8001` *(HTTPS later)* | Private remote-ish access. Mac runs Tailscale; iPhone runs Tailscale. The Mac is reachable at its tailnet name from any network. |

All three profiles hit the same FastAPI process at container port `8000`, published on host port `8001`.

The canonical reachability check on every profile:

```http
GET /api/v1/health
```

This is what the Connect screen probes before declaring success, and what `scripts/mobile_network_check.sh` (PHASE-PHONE-01B) verifies from the Mac side.

---

## 2. Default Compose state (current, safe)

`infra/docker-compose.yml` today binds **every** service to loopback. This is the right default and must not be loosened in the base file.

| Service | Host binding | Container port | Notes |
|---|---|---|---|
| api | `127.0.0.1:8001` | `8000` | FastAPI |
| web | `127.0.0.1:3000` | `3000` | Next.js |
| postgres | `127.0.0.1:5433` | `5432` | Operational truth |
| redis | `127.0.0.1:6379` | `6379` | Queue + cache |
| qdrant | `127.0.0.1:6333`, `127.0.0.1:6334` | `6333`, `6334` | Vector index (HTTP + gRPC) |
| kos-worker | (no published ports) | — | RQ worker |

Loopback means none of these are reachable from the iPhone over LAN or Tailscale.

---

## 3. `infra/docker-compose.mobile.yml`

PHONE-01B shipped this override file. It remains the contract for exposing the API to a physical iPhone while keeping data services loopback-only.

Purpose: expose **only** the API to the LAN interface, leaving all other services on loopback.

```yaml
# infra/docker-compose.mobile.yml
# Layer ON TOP of infra/docker-compose.yml when an iPhone on the same Wi-Fi
# needs to reach the backend. Never use this in production or on an untrusted
# network.

services:
  api:
    ports:
      - "0.0.0.0:8001:8000"   # API only — exposed to LAN
```

Run with:

```bash
docker compose \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.mobile.yml \
  up -d
```

Rules the override must obey:

1. **Only `api` is exposed to `0.0.0.0`.** Never override `postgres`, `redis`, `qdrant`, or `web` in the mobile file.
2. The override **adds** an `api.ports` entry; it does not change the container port (`8000`).
3. The base file is unchanged. Tearing down the mobile profile (`docker compose -f infra/docker-compose.yml up -d`) returns everything to loopback.
4. The Mac firewall (`System Settings → Network → Firewall`) should be on; explicit allow rule for port 8001 only.

For Tailscale-only access, the override is **not** required — Tailscale operates over its own interface and reaches the loopback-bound API through the Tailscale-on-Mac userspace forwarding (Tailscale Serve / built-in port-forwarding). See §6.

---

## 4. Strict exposure rule

> **Never expose anything but the API.** State the ports out loud so coders cannot misread:

| Service | Container port | Host port | LAN exposure allowed? |
|---|---|---|---|
| api | 8000 | 8001 | **Yes, via `docker-compose.mobile.yml` only.** |
| postgres | 5432 | 5433 | **Never.** |
| redis | 6379 | 6379 | **Never.** |
| qdrant HTTP | 6333 | 6333 | **Never.** |
| qdrant gRPC | 6334 | 6334 | **Never.** |
| web (Next.js) | 3000 | 3000 | **Never** (browser stays on the Mac). |

If any future phase needs to expose a service beyond the API to the device, that is a **separate phase decision** with explicit threat-model review. It does not happen by accident in `docker-compose.mobile.yml`.

---

## 5. iOS App Transport Security (ATS)

iOS requires HTTPS by default. Local development against `http://...` URLs needs `NSAppTransportSecurity` exceptions in `Info.plist`. PHONE-01C wired the current narrow exceptions into `apps/ios/project.yml`, which generates `Info.plist`.

### 5.1 Allowed strategy

- **Narrow** exceptions per host the user actually uses. Use `NSExceptionDomains`, not `NSAllowsArbitraryLoads`.
- Per-domain: enable `NSExceptionAllowsInsecureHTTPLoads` and (for `*.ts.net` Tailscale wildcards) `NSIncludesSubdomains`.
- Loopback (`127.0.0.1`) on Simulator does not strictly need an exception, but listing it makes the policy auditable.

Generated policy:

```xml
<key>NSAppTransportSecurity</key>
<dict>
  <key>NSExceptionDomains</key>
  <dict>
    <key>127.0.0.1</key>
    <dict>
      <key>NSExceptionAllowsInsecureHTTPLoads</key>
      <true/>
    </dict>
    <key>local</key>  <!-- mDNS .local for the Mac on LAN -->
    <dict>
      <key>NSExceptionAllowsInsecureHTTPLoads</key>
      <true/>
      <key>NSIncludesSubdomains</key>
      <true/>
    </dict>
    <key>ts.net</key>  <!-- Tailscale magic DNS suffix -->
    <dict>
      <key>NSExceptionAllowsInsecureHTTPLoads</key>
      <true/>
      <key>NSIncludesSubdomains</key>
      <true/>
    </dict>
  </dict>
</dict>
```

### 5.2 What is forbidden

- `NSAllowsArbitraryLoads = true` for shipping builds.
- Adding an exception "just in case" for a domain the app doesn't use.
- Leaving HTTP exceptions in place once a TLS-fronted profile exists.

### 5.3 Removal plan

Once a Tailscale HTTPS or self-hosted TLS profile lands (post-MVP):

1. Switch the Tailscale base URL to `https://<mac-tailnet-name>` (Tailscale issues automatic certs via MagicDNS).
2. Remove the `ts.net` exception from `Info.plist`.
3. Keep loopback and `local` exceptions only as long as the LAN profile is supported.

---

## 6. Tailscale profile notes

- The Mac runs the Tailscale client and is part of the user's tailnet.
- The iPhone runs the Tailscale iOS app and is logged into the same tailnet.
- The Mac is reachable from the iPhone at `<mac-tailnet-name>` (e.g. `mymac.tail1234.ts.net`).
- For the iPhone to reach the API, **either**:
  - Run the LAN override (`docker-compose.mobile.yml`) so the API binds `0.0.0.0:8001`, **and** ensure the Mac firewall allows Tailscale-interface traffic to port 8001; **or**
  - Use Tailscale Serve / Funnel-style port-forwarding from the tailnet name to `127.0.0.1:8001`, which keeps the API on loopback at the Docker layer and lets Tailscale userspace handle exposure.
- Tailscale Funnel (public-internet exposure) is **not** part of MVP. Tailnet-only.

---

## 7. Reachability checks

### 7.1 From the Mac (developer-side)

`scripts/mobile_network_check.sh` (Phase 01B) wraps these checks:

```bash
# 1. Is the API up on loopback?
curl -fsS http://127.0.0.1:8001/api/v1/health

# 2. Is the mobile override running (API also on LAN)?
lsof -nP -iTCP:8001 -sTCP:LISTEN
#   Expect: a row with *:8001 if the mobile override is active.

# 3. Are sensitive ports loopback-only?
lsof -nP -iTCP:5433 -sTCP:LISTEN | grep -v '127.0.0.1' \
  && echo "WARN: postgres exposed beyond loopback"
lsof -nP -iTCP:6379 -sTCP:LISTEN | grep -v '127.0.0.1' \
  && echo "WARN: redis exposed beyond loopback"
lsof -nP -iTCP:6333 -sTCP:LISTEN | grep -v '127.0.0.1' \
  && echo "WARN: qdrant exposed beyond loopback"

# 4. Print suggested base URLs.
echo "Simulator: http://127.0.0.1:8001"
echo "LAN:       http://$(ipconfig getifaddr en0):8001"
echo "Tailscale: http://$(tailscale status --self --json 2>/dev/null \
  | jq -r '.Self.DNSName // empty' | sed 's/\.$//'):8001"
```

### 7.2 From the iPhone

The Connect screen calls `GET /api/v1/health` and shows the JSON status. Any non-200 response surfaces a profile-specific troubleshooting hint.

---

## 8. Threat model summary

| Threat | Mitigation |
|---|---|
| Untrusted Wi-Fi attacker scrapes API. | Bearer token required for every endpoint except `/health` and `/auth/mobile-login`. ATS exception narrow to known hosts. Tailscale profile bypasses LAN exposure entirely. |
| Lateral attacker on the LAN finds postgres/redis/qdrant. | These services are bound to loopback in the base Compose file and never overridden. The mobile override only touches `api`. |
| Lost iPhone replays bearer token. | Token is opaque, server-side revocable via `POST /auth/mobile-logout`, and stored in iOS Keychain. Tokens have `expires_at`. |
| User leaves mobile Compose override on by accident. | The override is a separate file requiring an explicit `-f infra/docker-compose.mobile.yml` flag. Restart without it returns to loopback. |
| Logging leaks token. | Hard rule: never log the bearer token (enforced by Phase 01A tests). |

---

## 9. Phase ownership

| Item | Phase |
|---|---|
| This document | PHONE-00, refreshed by PHONE-07 |
| `infra/docker-compose.mobile.yml` | PHONE-01B |
| `scripts/mobile_network_check.sh` | PHONE-01B |
| `apps/ios/project.yml` ATS exceptions | PHONE-01C |
| Bearer auth on `/api/v1/auth/mobile-login` etc. | PHONE-01A |

---

## 10. Operator runbook (PHONE-01B)

The override file and check script designed in §3 / §7 are now live. This runbook is the operator's day-to-day reference.

### 10.1 Simulator-only (default — safest)

Loopback `127.0.0.1:8001` is reachable from the iOS Simulator on the same Mac. No override needed.

```bash
docker compose -f infra/docker-compose.yml up -d
bash scripts/mobile_network_check.sh
```

Expected script output: every check `PASS`; section 5 reports `simulator-only profile (loopback only)`; the final summary prints the suggested Simulator URL (and LAN / Tailscale URLs as informational).

### 10.2 Same-Wi-Fi (physical iPhone on the LAN)

Layer the mobile override on top of the base file:

```bash
docker compose \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.mobile.yml \
  up -d
bash scripts/mobile_network_check.sh
```

Expected: API also reachable on `0.0.0.0:8001`; section 5 reports `mobile profile ACTIVE (LAN reachable)`; the safety audit still `PASS`es on postgres / redis / qdrant (loopback only). Configure the iPhone Connect screen with the LAN URL printed at the end (`http://<mac-lan-ip>:8001`).

The mobile override uses Compose's `!override` directive on `api.ports` so the merged port list contains only `0.0.0.0:8001:8000`. Without `!override`, Compose would *add* the new port to the base `127.0.0.1:8001:8000` and Docker would fail with `address already in use` (the two bindings collide on the same host port). A `0.0.0.0` binding still accepts loopback traffic, so the Simulator URL keeps working when the override is active.

macOS firewall: keep on. The first run will prompt to allow `com.docker.backend` to accept incoming connections on port 8001.

### 10.3 Tailscale (private remote)

The mobile override is **optional** for Tailscale. Two viable shapes:

- **Override on:** API binds `0.0.0.0:8001`; Tailscale tunnel reaches it on the tailnet IP. Use the same `up -d` command as §10.2.
- **Override off:** Use `tailscale serve` to forward `<mac-tailnet-name>:8001` → `127.0.0.1:8001`. API stays loopback-bound at the Docker layer; Tailscale userspace owns LAN exposure.

The override-off shape is preferred when only Tailscale clients ever connect, because the API stays off the LAN entirely.

### 10.4 Teardown — return to loopback-only

```bash
docker compose -f infra/docker-compose.yml up -d
bash scripts/mobile_network_check.sh
```

Bringing the stack up *without* the `-f infra/docker-compose.mobile.yml` flag re-applies the base loopback binding. Verify with `lsof -nP -iTCP:8001 -sTCP:LISTEN` — only `127.0.0.1:8001` should be listed, and the script's section 5 should report `simulator-only profile`.

### 10.5 What the check script verifies

`scripts/mobile_network_check.sh` exits **non-zero** if any of the following is true:

1. The API is not reachable on `http://127.0.0.1:8001/api/v1/health`.
2. **Any** of postgres `:5433`, redis `:6379`, qdrant HTTP `:6333`, qdrant gRPC `:6334` is listening on something other than `127.0.0.1` / `[::1]`.

LAN / Tailscale URL suggestions, and the `:8001` binding readout, are informational — they emit `WARN` (not `FAIL`) when the profile is unavailable. A missing LAN IP (Wi-Fi off) or a missing `tailscale` binary will not fail the script.

### 10.6 Optional env: `MOBILE_API_BIND_HOST`

Reserved name for a future variant of `infra/docker-compose.mobile.yml` that interpolates the bind host (e.g. binding to a specific LAN interface address instead of `0.0.0.0`). PHASE-PHONE-01B does not consume this variable; the current override hard-codes `0.0.0.0:8001`. It is documented in `infra/.env.example` so operators know the name is reserved.
