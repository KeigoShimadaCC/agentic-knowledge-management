#!/usr/bin/env bash
# Install (or reinstall) an MCP server package into the kos-api container's venv.
#
# Use this after `docker compose up -d api` recreates the container — the
# kos-api-venv volume is re-seeded from the image and any prior `uv pip install`
# performed via `docker exec` is wiped.
#
# Usage:
#   scripts/install-mcp-in-api.sh <pypi-package-name>
#   scripts/install-mcp-in-api.sh <absolute-path-to-source-tree>
#
# Examples:
#   scripts/install-mcp-in-api.sh some-published-mcp
#   scripts/install-mcp-in-api.sh /tmp/anthropic-news-mcp
#
# See docs/MCP_CONNECTIONS.md for the surrounding playbook.

set -euo pipefail

container="${KOS_API_CONTAINER:-kos-api}"
venv_python="/app/.venv/bin/python"

target="${1:-}"
if [[ -z "$target" ]]; then
  echo "usage: $0 <pypi-package | absolute-path-to-source>" >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$container"; then
  echo "error: container '$container' is not running" >&2
  echo "       start it with: docker compose -f infra/docker-compose.yml up -d api" >&2
  exit 1
fi

if [[ "$target" = /* && -d "$target" ]]; then
  name="$(basename "$target")"
  dest="/opt/$name"
  echo "==> Copying source tree into $container:$dest"
  docker exec "$container" mkdir -p "$dest"
  docker cp "$target/." "$container:$dest/"
  echo "==> Installing from $dest"
  docker exec "$container" uv pip install --python "$venv_python" "$dest"
else
  if [[ "$target" = /* ]]; then
    echo "error: $target looks like a path but is not a directory" >&2
    exit 1
  fi
  echo "==> Installing $target from PyPI"
  docker exec "$container" uv pip install --python "$venv_python" "$target"
fi

echo
echo "==> Done. Recently installed entry points (likely candidates for the 'command' field):"
docker exec "$container" sh -c \
  "ls -t /app/.venv/bin/ | head -20"
