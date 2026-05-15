#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/infra/.env"

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

KOS_ROOT="${HOME}/KnowledgeOS"
LIBRARY_ROOT="${LIBRARY_ROOT:-${KOS_ROOT}/library}"
POSTGRES_USER="${POSTGRES_USER:-kos}"
POSTGRES_DB="${POSTGRES_DB:-knowledgeos}"

ts="$(date +%Y%m%d-%H%M%S)"
out="${KOS_ROOT}/backups/${ts}"
mkdir -p "${out}"

echo "Writing KnowledgeOS backup to ${out}"

docker compose -f "${ROOT_DIR}/infra/docker-compose.yml" exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc \
  > "${out}/postgres.dump"

if [ -d "${LIBRARY_ROOT}" ]; then
  tar --exclude "tmp" -C "$(dirname "${LIBRARY_ROOT}")" -czf "${out}/library.tar.gz" \
    "$(basename "${LIBRARY_ROOT}")"
else
  echo "Library root not found: ${LIBRARY_ROOT}" > "${out}/library-missing.txt"
fi

if curl -fsS -X POST "http://127.0.0.1:6333/collections/knowledgeos_chunks/snapshots" \
  > "${out}/qdrant-snapshot.json"; then
  echo "Qdrant snapshot metadata written."
else
  echo "Qdrant snapshot skipped; collection or service is unavailable." \
    > "${out}/qdrant-snapshot-skipped.txt"
fi

cat > "${out}/README.txt" <<EOF
KnowledgeOS backup created at ${ts}

Files:
- postgres.dump: pg_dump custom-format logical backup for ${POSTGRES_DB}
- library.tar.gz: compressed copy of ${LIBRARY_ROOT}, excluding tmp/
- qdrant-snapshot.json or qdrant-snapshot-skipped.txt: best-effort derived-index snapshot

Postgres plus the library tarball are canonical. Qdrant is rebuildable from Postgres.
EOF

echo "Backup complete: ${out}"
