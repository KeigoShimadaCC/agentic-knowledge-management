#!/usr/bin/env bash
# scripts/mobile_simulator_boot.sh
#
# Idempotent: boot iPhone simulator, build KnowledgeOS, install, and launch.
# Companion: docs/MOBILE_QA.md
#
# Env:
#   SIMULATOR_NAME  (default: iPhone 16)
#   SCHEME          (default: KnowledgeOS)
#   BUNDLE_ID       (default: com.knowledgeos.ios)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IOS_DIR="${REPO_ROOT}/apps/ios"
SIMULATOR_NAME="${SIMULATOR_NAME:-iPhone 16}"
SCHEME="${SCHEME:-KnowledgeOS}"
BUNDLE_ID="${BUNDLE_ID:-com.knowledgeos.ios}"
DERIVED_DATA="${IOS_DIR}/.build/DerivedData"

if [ -t 1 ]; then
  C_RESET=$'\033[0m'
  C_GREEN=$'\033[32m'
  C_BOLD=$'\033[1m'
else
  C_RESET="" C_GREEN="" C_BOLD=""
fi

section() { printf "\n%s%s%s\n" "$C_BOLD" "$1" "$C_RESET"; }

section "1. Resolve simulator: ${SIMULATOR_NAME}"

export SIM_NAME="${SIMULATOR_NAME}"
UDID="$(xcrun simctl list devices available -j \
  | python3 -c "
import json, sys, os
name = os.environ.get('SIM_NAME', '')
data = json.load(sys.stdin)
for runtime, devices in data.get('devices', {}).items():
    if 'iOS' not in runtime:
        continue
    for d in devices:
        if d.get('name') == name and d.get('isAvailable', True):
            print(d['udid'])
            sys.exit(0)
sys.exit(1)
" 2>/dev/null || true)"

if [ -z "${UDID}" ]; then
  UDID="$(xcrun simctl list devices available \
    | grep -F "${SIMULATOR_NAME} (" \
    | head -1 \
    | sed -E 's/.*\(([A-F0-9-]{36})\).*/\1/' || true)"
fi

if [ -z "${UDID}" ]; then
  echo "ERROR: No available simulator named '${SIMULATOR_NAME}'." >&2
  echo "Create one with:" >&2
  echo "  xcrun simctl create \"${SIMULATOR_NAME}\" \\" >&2
  echo "    \"com.apple.CoreSimulator.SimDeviceType.iPhone-16\" \\" >&2
  echo "    \"<runtime-from: xcrun simctl list runtimes>\"" >&2
  exit 1
fi

printf "  UDID: %s\n" "${UDID}"

section "2. Boot simulator (idempotent)"

BOOT_STATUS="$(xcrun simctl list devices -j \
  | python3 -c "
import json, sys
udid = sys.argv[1]
data = json.load(sys.stdin)
for devices in data.get('devices', {}).values():
    for d in devices:
        if d.get('udid') == udid:
            print(d.get('state', 'Unknown'))
            sys.exit(0)
" "${UDID}" 2>/dev/null || echo "Unknown")"

if [ "${BOOT_STATUS}" != "Booted" ]; then
  xcrun simctl boot "${UDID}" 2>/dev/null || true
  xcrun simctl bootstatus "${UDID}" -b
else
  printf "  Already booted.\n"
fi

xcrun simctl bootstatus booted -b >/dev/null 2>&1 || true

section "3. Build ${SCHEME}"

if ! command -v xcodegen >/dev/null 2>&1; then
  echo "ERROR: xcodegen not found (brew install xcodegen)" >&2
  exit 1
fi

if [ ! -d "${IOS_DIR}/KnowledgeOS.xcodeproj" ]; then
  (cd "${IOS_DIR}" && xcodegen generate)
fi

(
  cd "${IOS_DIR}"
  xcodebuild \
    -project KnowledgeOS.xcodeproj \
    -scheme "${SCHEME}" \
    -destination "platform=iOS Simulator,name=${SIMULATOR_NAME}" \
    -derivedDataPath "${DERIVED_DATA}" \
    build \
    CODE_SIGNING_ALLOWED=NO
)

APP_PATH="${DERIVED_DATA}/Build/Products/Debug-iphonesimulator/${SCHEME}.app"
if [ ! -d "${APP_PATH}" ]; then
  echo "ERROR: Built app not found at ${APP_PATH}" >&2
  exit 1
fi

printf "  App: %s\n" "${APP_PATH}"

section "4. Install and launch"

xcrun simctl install booted "${APP_PATH}" 2>/dev/null || xcrun simctl install "${UDID}" "${APP_PATH}"

# Terminate if already running, then launch
xcrun simctl terminate booted "${BUNDLE_ID}" 2>/dev/null || true
LAUNCH_OUTPUT="$(xcrun simctl launch booted "${BUNDLE_ID}" 2>&1)" || true
printf "  %s\n" "${LAUNCH_OUTPUT}"

section "Done"
printf "%sOK%s — Simulator booted, app installed and launched.\n" "${C_GREEN}" "${C_RESET}"
printf "  UDID:      %s\n" "${UDID}"
printf "  Bundle ID: %s\n" "${BUNDLE_ID}"
printf "  Screenshot: bash scripts/mobile_simulator_screenshot.sh\n"
