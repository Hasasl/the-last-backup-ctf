#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
backup="runtime/backups/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup"
chmod 700 "$backup"
umask 077
# Quiesce scoring and uploads so both backups represent the same point in time.
docker compose -f compose.control.yml stop control-web ctfd
trap 'docker compose -f compose.control.yml start ctfd control-web' EXIT
docker compose -f compose.control.yml exec -T database sh -c 'exec mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction ctfd' > "$backup/ctfd.sql"
docker compose -f compose.control.yml run --rm --no-deps --entrypoint tar ctfd -C /var/uploads -cf - . > "$backup/uploads.tar"
echo "Backup saved in $backup. Keep it with the private .env and a release-register copy."
