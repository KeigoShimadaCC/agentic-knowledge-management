#!/usr/bin/env bash
# scripts/mobile_qa_phone08.sh
#
# PHONE-08 cross-platform parity simulator QA: capture screenshots for login,
# home, search, detail, capture, edit, AI, and settings without requiring idb.
#
# Prereqs:
#   - bash scripts/mobile_simulator_boot.sh   # iPhone 16 booted, app installed
#   - Signed in as demo@example.com (or your test user)
#
# Pair with ios-simulator MCP prompts in docs/MOBILE_QA.md for ui_describe_all when idb is available.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${REPO_ROOT}/.tmp/mobile-qa/phone-08/$(date +%Y%m%d-%H%M%S)"

mkdir -p "${OUT_DIR}"

if ! xcrun simctl list devices booted 2>/dev/null | grep -q Booted; then
  echo "ERROR: No booted simulator. Run: bash scripts/mobile_simulator_boot.sh" >&2
  exit 1
fi

shot() {
  local name="$1"
  local path="${OUT_DIR}/${name}.png"
  xcrun simctl io booted screenshot "${path}"
  printf "  saved: %s\n" "${path}"
}

cat <<'EOF'
PHONE-08 simulator QA (simctl screenshots)
==========================================
Walk the app on the booted iPhone 16 simulator. After each step, press <Enter>
to capture a screenshot under .tmp/mobile-qa/phone-08/.

Expected kos.* identifiers (see AccessibilityID.swift):
  login: kos.login.*
  home: kos.home.*
  search: kos.search.*
  detail: kos.object.* / kos.page.*
  capture: kos.capture.*
  edit: kos.object.edit*
  AI: kos.ai.*
  settings: kos.settings.*
EOF

read -r -p "1. Login screen (signed out). Press <Enter>..."
shot "01-login"

read -r -p "2. Login filled (optional). Press <Enter>..."
shot "02-login-filled"

read -r -p "3. Home tab with recent list. Press <Enter>..."
shot "03-home"

read -r -p "4. Search tab with query + results. Press <Enter>..."
shot "04-search"

read -r -p "5. Object/page detail. Press <Enter>..."
shot "05-detail"

read -r -p "6. Capture tab (note or upload). Press <Enter>..."
shot "06-capture"

read -r -p "7. Edit metadata or body sheet. Press <Enter>..."
shot "07-edit"

read -r -p "8. AI tab (Ask KB or actions). Press <Enter>..."
shot "08-ai"

read -r -p "9. Settings tab. Press <Enter>..."
shot "09-settings"

printf "\nDone. Screenshots in %s\n" "${OUT_DIR}"
printf "Optional: run ios-simulator MCP ui_describe_all on each screen when idb is installed.\n"
