#!/usr/bin/env bash
# scripts/mobile_simulator_screenshot.sh
#
# Capture a PNG from the booted iOS Simulator into .tmp/mobile-qa/
# Companion: docs/MOBILE_QA.md

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${REPO_ROOT}/.tmp/mobile-qa"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUT_FILE="${OUT_DIR}/${TIMESTAMP}.png"

mkdir -p "${OUT_DIR}"

if ! xcrun simctl list devices booted 2>/dev/null | grep -q Booted; then
  echo "ERROR: No booted simulator. Run: bash scripts/mobile_simulator_boot.sh" >&2
  exit 1
fi

xcrun simctl io booted screenshot "${OUT_FILE}"

if [ ! -f "${OUT_FILE}" ]; then
  echo "ERROR: Screenshot was not created at ${OUT_FILE}" >&2
  exit 1
fi

printf "Screenshot saved: %s\n" "${OUT_FILE}"
