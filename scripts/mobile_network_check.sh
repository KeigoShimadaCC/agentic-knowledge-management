#!/usr/bin/env bash
# scripts/mobile_network_check.sh
#
# Preflight reachability + safety audit for the mobile networking profile
# (PHASE-PHONE-01B). Run from the Mac with the Docker stack up.
#
# Exits 0 if every safety check PASSes (postgres / redis / qdrant remain
# loopback-bound and the API is reachable). Exits 1 if any safety check FAILs.
# WARN entries do not fail the script.
#
# Cross-checks (optional, not required for PASS):
#   docker port kos-api      # mirrors the LAN binding check
#   docker port kos-postgres # mirrors the safety audit
#
# Companion doc: docs/MOBILE_NETWORKING.md §10 (operator runbook).

set -euo pipefail

# ----- colors (tty only) ------------------------------------------------------
if [ -t 1 ]; then
  C_RESET=$'\033[0m'
  C_GREEN=$'\033[32m'
  C_YELLOW=$'\033[33m'
  C_RED=$'\033[31m'
  C_BOLD=$'\033[1m'
else
  C_RESET="" C_GREEN="" C_YELLOW="" C_RED="" C_BOLD=""
fi

PASS_LABEL="${C_GREEN}PASS${C_RESET}"
WARN_LABEL="${C_YELLOW}WARN${C_RESET}"
FAIL_LABEL="${C_RED}FAIL${C_RESET}"

fail_count=0
warn_count=0

print_pass() { printf "  [%s] %s\n" "$PASS_LABEL" "$1"; }
print_warn() { printf "  [%s] %s\n" "$WARN_LABEL" "$1"; warn_count=$((warn_count + 1)); }
print_fail() { printf "  [%s] %s\n" "$FAIL_LABEL" "$1"; fail_count=$((fail_count + 1)); }

section() { printf "\n%s%s%s\n" "$C_BOLD" "$1" "$C_RESET"; }

# ----- 1. API loopback reachability ------------------------------------------
section "1. API reachable on loopback (http://127.0.0.1:8001/api/v1/health)"

if curl -fsS --max-time 5 http://127.0.0.1:8001/api/v1/health >/dev/null 2>&1; then
  print_pass "API responded 2xx on 127.0.0.1:8001"
else
  print_fail "API did NOT respond on 127.0.0.1:8001 — is the stack up? (docker compose -f infra/docker-compose.yml up -d)"
fi

# ----- 2. LAN URL suggestion --------------------------------------------------
section "2. Suggested LAN base URL (same-Wi-Fi profile)"

lan_ip=""
for iface in en0 en1; do
  candidate=$(ipconfig getifaddr "$iface" 2>/dev/null || true)
  if [ -n "$candidate" ]; then
    lan_ip="$candidate"
    printf "  interface %s → %s\n" "$iface" "$candidate"
    break
  fi
done

if [ -n "$lan_ip" ]; then
  print_pass "LAN URL: http://${lan_ip}:8001"
else
  print_warn "No LAN IP on en0/en1 — Wi-Fi off? (no FAIL: LAN profile is optional)"
fi

# ----- 3. Tailscale URL suggestion -------------------------------------------
section "3. Suggested Tailscale base URL (private remote profile)"

ts_name=""   # reused in the summary
if ! command -v tailscale >/dev/null 2>&1; then
  print_warn "tailscale not installed — Tailscale profile unavailable (optional)"
elif ! command -v jq >/dev/null 2>&1; then
  print_warn "jq not installed — cannot parse tailscale status JSON (install: brew install jq)"
else
  # Retry once: tailscaled occasionally returns a partial status on a cold first call.
  for _ in 1 2; do
    ts_status=$(tailscale status --json 2>/dev/null || true)
    [ -z "$ts_status" ] && { sleep 1; continue; }
    ts_name=$(printf '%s' "$ts_status" | jq -r '.Self.DNSName // empty' | sed 's/\.$//')
    [ -n "$ts_name" ] && break
    sleep 1
  done
  if [ -n "$ts_name" ]; then
    print_pass "Tailscale URL: http://${ts_name}:8001"
  else
    print_warn "tailscale not running, not logged in, or returned no Self.DNSName — skip"
  fi
fi

# ----- 4. Safety audit: sensitive ports must NOT bind 0.0.0.0 ----------------
section "4. Safety audit — sensitive ports MUST remain loopback-only"

# port -> human label
audit_ports=("5433:postgres" "6379:redis" "6333:qdrant-http" "6334:qdrant-grpc")

for entry in "${audit_ports[@]}"; do
  port="${entry%%:*}"
  label="${entry#*:}"
  listeners=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [ -z "$listeners" ]; then
    print_warn "${label} (:${port}) — no listener (service not running?)"
    continue
  fi
  # Listener "Name" column looks like "127.0.0.1:5433" or "*:5433" or "[::1]:5433".
  bad=$(printf '%s\n' "$listeners" | awk 'NR>1 {print $9}' \
        | grep -vE '^(127\.0\.0\.1|\[::1\]):' || true)
  if [ -z "$bad" ]; then
    print_pass "${label} (:${port}) — loopback only"
  else
    print_fail "${label} (:${port}) — bound BEYOND loopback:"
    printf '%s\n' "$bad" | sed 's/^/        /'
  fi
done

# ----- 5. API exposure status (informational) --------------------------------
section "5. API exposure on :8001 (informational — profile detector)"

api_listeners=$(lsof -nP -iTCP:8001 -sTCP:LISTEN 2>/dev/null || true)
if [ -z "$api_listeners" ]; then
  print_warn "no listener on :8001 (the API check above already FAILed)"
else
  binds=$(printf '%s\n' "$api_listeners" | awk 'NR>1 {print $9}' | sort -u)
  printf "  bindings:\n%s\n" "$binds" | sed 's/^/    /'
  if printf '%s\n' "$binds" | grep -qE '^\*:8001$|^0\.0\.0\.0:8001$'; then
    printf "  → mobile profile %sACTIVE%s (LAN reachable)\n" "$C_BOLD" "$C_RESET"
  else
    printf "  → simulator-only profile (loopback only)\n"
  fi
fi

# ----- 6. Summary -------------------------------------------------------------
section "Summary"

printf "  FAIL: %d   WARN: %d\n" "$fail_count" "$warn_count"

if [ "$fail_count" -gt 0 ]; then
  printf "\n%sFAIL%s — see entries above. Common fixes:\n" "$C_RED" "$C_RESET"
  printf "  • API not reachable → \`docker compose -f infra/docker-compose.yml up -d\`\n"
  printf "  • Sensitive port exposed → check infra/docker-compose.mobile.yml; it must\n"
  printf "    ONLY override \`api.ports\`. Never add postgres/redis/qdrant/worker/web.\n"
  exit 1
fi

printf "\n%sOK%s — base URLs to try in the iPhone Connect screen:\n" "$C_GREEN" "$C_RESET"
printf "  Simulator: http://127.0.0.1:8001\n"
[ -n "$lan_ip" ] && printf "  LAN:       http://%s:8001\n" "$lan_ip"
[ -n "$ts_name" ] && printf "  Tailscale: http://%s:8001\n" "$ts_name"
exit 0
