#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Bu betik root olarak calismali: sudo $0" >&2
    exit 2
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVIRONMENT_DIRECTORY="/etc/butik"
SQLITE_ENVIRONMENT_FILE="$ENVIRONMENT_DIRECTORY/butik.env.sqlite"
POSTGRES_ENVIRONMENT_FILE="$ENVIRONMENT_DIRECTORY/butik.env.postgres"
ACTIVE_ENVIRONMENT_FILE="$ENVIRONMENT_DIRECTORY/butik.env"
SERVICE_OVERRIDE_DIRECTORY="/etc/systemd/system/butik.service.d"
SERVICE_OVERRIDE_FILE="$SERVICE_OVERRIDE_DIRECTORY/database.conf"
DATABASE_NAME="lafemme_prod"
DATABASE_ROLE="lafemme_prod"
SQLITE_URL="sqlite:////home/butikadmin/butik_app/data/lafemme.db"

if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    echo "Uygulama sanal ortami bulunamadi: $PROJECT_ROOT/.venv/bin/python" >&2
    exit 2
fi
if [[ ! -f "$PROJECT_ROOT/instance/auth.json" ]]; then
    echo "Mevcut giris ayari bulunamadi: $PROJECT_ROOT/instance/auth.json" >&2
    exit 2
fi
if ! command -v psql >/dev/null 2>&1; then
    echo "PostgreSQL istemcisi bulunamadi. Once postgresql paketini kurun." >&2
    exit 2
fi
if runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname = '$DATABASE_NAME'" | grep -qx "1"; then
    echo "Guvenlik durdurmasi: '$DATABASE_NAME' zaten mevcut. Mevcut veritabani degistirilmedi." >&2
    exit 2
fi

database_password="$(openssl rand -hex 32)"
secret_key="$(openssl rand -hex 48)"
postgres_url="postgresql+psycopg://${DATABASE_ROLE}:${database_password}@127.0.0.1:5432/${DATABASE_NAME}"

install -d -m 700 "$ENVIRONMENT_DIRECTORY"
umask 077
cat > "$SQLITE_ENVIRONMENT_FILE" <<EOF
APP_ENV=production
SECRET_KEY=$secret_key
DATABASE_URL=$SQLITE_URL
EOF
cat > "$POSTGRES_ENVIRONMENT_FILE" <<EOF
APP_ENV=production
SECRET_KEY=$secret_key
DATABASE_URL=$postgres_url
POSTGRES_EXPECTED_DATABASE=$DATABASE_NAME
EOF
chmod 600 "$SQLITE_ENVIRONMENT_FILE" "$POSTGRES_ENVIRONMENT_FILE"
ln -sfn "$SQLITE_ENVIRONMENT_FILE" "$ACTIVE_ENVIRONMENT_FILE"

runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "CREATE ROLE $DATABASE_ROLE LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD '$database_password';"
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE $DATABASE_NAME OWNER $DATABASE_ROLE ENCODING 'UTF8';"

install -d -m 755 "$SERVICE_OVERRIDE_DIRECTORY"
cat > "$SERVICE_OVERRIDE_FILE" <<EOF
[Service]
EnvironmentFile=$ACTIVE_ENVIRONMENT_FILE
EOF
chmod 644 "$SERVICE_OVERRIDE_FILE"
systemctl daemon-reload

echo "POSTGRES_BOOTSTRAP_BASARILI database=$DATABASE_NAME role=$DATABASE_ROLE"
echo "AKTIF_UYGULAMA_VERITABANI=SQLite"
echo "SONRAKI_ADIM=SQLite snapshot ile PostgreSQL aktarim provasi"
