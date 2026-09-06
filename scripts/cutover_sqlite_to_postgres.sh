#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 2 || $# -lt 1 ]]; then
    echo "Kullanim: sudo $0 /mutlak/yol/lafemme_canli_snapshot.db [/etc/butik/butik.env.postgres]" >&2
    exit 2
fi

SOURCE_PATH="$1"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
FLASK="$PROJECT_ROOT/.venv/bin/flask"
ENVIRONMENT_FILE="${2:-/etc/butik/butik.env.postgres}"

if [[ ! -r "$ENVIRONMENT_FILE" ]]; then
    echo "PostgreSQL environment dosyasi okunamiyor: $ENVIRONMENT_FILE" >&2
    exit 2
fi

set -a
# This root-owned file contains the cutover-only PostgreSQL connection URL.
source "$ENVIRONMENT_FILE"
set +a

EXPECTED_DATABASE="${POSTGRES_EXPECTED_DATABASE:-lafemme_prod}"

if [[ ! -f "$SOURCE_PATH" ]]; then
    echo "SQLite snapshot bulunamadi: $SOURCE_PATH" >&2
    exit 2
fi
if [[ -z "${DATABASE_URL:-}" || "$DATABASE_URL" != postgresql+psycopg://* ]]; then
    echo "DATABASE_URL PostgreSQL psycopg baglanti dizgesi olmali." >&2
    exit 2
fi

read -r -p "Hedef PostgreSQL veritabani '$EXPECTED_DATABASE' tamamen yenilenecek. Devam icin CANLI_POSTGRES_AKTAR yazin: " confirmation
if [[ "$confirmation" != "CANLI_POSTGRES_AKTAR" ]]; then
    echo "Cutover kullanici tarafindan iptal edildi."
    exit 1
fi

cd "$PROJECT_ROOT"
"$FLASK" --app run.py db upgrade
"$PYTHON" scripts/sqlite_to_postgres.py \
    --source "$SOURCE_PATH" \
    --target-url "$DATABASE_URL" \
    --expected-target-database "$EXPECTED_DATABASE" \
    --confirm-replace-target
"$PYTHON" scripts/verify_postgres_cutover.py \
    --source "$SOURCE_PATH" \
    --target-url "$DATABASE_URL" \
    --expected-target-database "$EXPECTED_DATABASE"

echo "POSTGRES_CUTOVER_HAZIR: Servis DATABASE_URL ile PostgreSQL'e yonlendirilebilir."
