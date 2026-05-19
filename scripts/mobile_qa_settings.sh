#!/usr/bin/env bash
# scripts/mobile_qa_settings.sh
#
# PHASE-16 Settings simulator QA: capture screenshots for secrets, prompts,
# feature models, MCP, and background AI without requiring idb.
#
# Prereqs:
#   - bash scripts/mobile_simulator_boot.sh   # iPhone 16 booted, app installed
#   - Signed in as demo@example.com (or your test user)
#
# Pair with ios-simulator MCP prompts in docs/MOBILE_QA.md when idb is available.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${REPO_ROOT}/.tmp/mobile-qa/settings-16/$(date +%Y%m%d-%H%M%S)"

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
PHASE-16 Settings simulator QA (simctl screenshots)
=================================================
Walk the Settings tab on the booted iPhone 16 simulator. After each step, press <Enter>
to capture a screenshot under .tmp/mobile-qa/settings-16/.

Expected kos.* identifiers (see AccessibilityID.swift / SettingsTab.swift):
  root: kos.settings.screen, kos.settings.loaded, kos.settings.saveKeys
  prompts: kos.settings.prompt.summarize.page, kos.settings.promptEditor, kos.settings.promptSave
  features: kos.settings.feature.summarize, kos.settings.featureEditor, kos.settings.featureModel, kos.settings.featureSave
  mcp: kos.settings.mcp.test.*
  background: kos.settings.backgroundSave

UITest relaunch flags (see docs/MOBILE_QA.md):
  -KOS_UI_TAB=settings  -ui-testing-single-tab  -ui-testing-skip-reset
EOF

read -r -p "1. Settings root (secrets + save keys visible). Press <Enter>..."
shot "01-settings-root"

read -r -p "2. Summarize Page prompt editor open. Press <Enter>..."
shot "02-prompt-editor"

read -r -p "3. Summarization feature model editor open. Press <Enter>..."
shot "03-feature-editor"

read -r -p "4. MCP test button tapped (optional). Press <Enter>..."
shot "04-mcp-test"

read -r -p "5. Background AI section (scroll if needed). Press <Enter>..."
shot "05-background-ai"

printf "\nDone. Screenshots in %s\n" "${OUT_DIR}"
printf "Optional: run ios-simulator MCP ui_describe_all on each screen when idb is installed.\n"
