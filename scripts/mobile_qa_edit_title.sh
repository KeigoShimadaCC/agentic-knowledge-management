#!/usr/bin/env bash
# scripts/mobile_qa_edit_title.sh
#
# PHONE-04 edit-lite smoke: capture before/after screenshots of the edit-title flow.
# Prereqs:
#   - bash scripts/mobile_simulator_boot.sh   # iPhone 16 booted, app installed
#   - The KnowledgeOS app is signed-in and shows Home with at least one object.
#
# This script does NOT drive the simulator UI — pair it with the simulator-MCP
# prompts in docs/MOBILE_QA.md to walk Home → object detail → Edit → save.
# Screenshots land under .tmp/mobile-qa/edit-title/<timestamp>/.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${REPO_ROOT}/.tmp/mobile-qa/edit-title/${TIMESTAMP}"

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
PHONE-04 edit-title smoke
=========================
Use this script alongside the iOS-Simulator MCP prompts. After each manual step,
press <Enter> and we'll capture a screenshot.
EOF

read -r -p "1. App is on Home with object list visible. Press <Enter> to capture..."
shot "01-home"

read -r -p "2. Open the first object. Press <Enter> to capture object detail..."
shot "02-object-detail"

read -r -p "3. Tap Edit (nav bar). Press <Enter> to capture metadata sheet..."
shot "03-edit-sheet"

read -r -p "4. Type a new title + (optional) add a tag. Press <Enter> to capture..."
shot "04-edit-changed"

read -r -p "5. Tap Save. Press <Enter> after sheet dismisses..."
shot "05-after-save"

read -r -p "6. Pop to Home, reopen the object. Press <Enter> to capture persisted state..."
shot "06-reopened"

printf "\nDone. Screenshots in %s\n" "${OUT_DIR}"
