#!/usr/bin/env bash
set -euo pipefail

LIBRARY_ROOT="${HOME}/KnowledgeOS/library"
KOS_ROOT="${HOME}/KnowledgeOS"

echo "=== KnowledgeOS Setup ==="
echo "Creating directory structure at ${KOS_ROOT}..."

mkdir -p "${LIBRARY_ROOT}/assets"
mkdir -p "${LIBRARY_ROOT}/tmp"
mkdir -p "${LIBRARY_ROOT}/exports"
mkdir -p "${KOS_ROOT}/backups"
mkdir -p "${KOS_ROOT}/logs"
mkdir -p "${KOS_ROOT}/data/kuzu"

echo "0.1.0" > "${KOS_ROOT}/.kos_version"

# Copy env example if .env doesn't exist
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_EXAMPLE="${SCRIPT_DIR}/../infra/.env.example"
ENV_FILE="${SCRIPT_DIR}/../infra/.env"

if [ ! -f "${ENV_FILE}" ]; then
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    # Substitute the placeholder username with the actual home path
    sed -i '' "s|/Users/YOUR_USERNAME|${HOME}|g" "${ENV_FILE}"
    echo "Created infra/.env — edit it to set your SESSION_SECRET"
else
    echo "infra/.env already exists — skipping copy"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit infra/.env and set SESSION_SECRET to a random 32+ char string"
echo "  2. Run: docker compose -f infra/docker-compose.yml up -d"
echo "  3. Open: http://localhost:3000"
