#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p runtime/certs
cd runtime/certs
if [ -e ca.key ] || [ -e control.key ] || [ -e verifier.key ]; then
  echo 'Certificate keys already exist; refusing to overwrite.' >&2
  exit 1
fi
umask 077
openssl req -x509 -newkey rsa:3072 -nodes -days 365 -keyout ca.key -out ca.crt -subj '/CN=Northstar Classroom CA'
for spec in control:192.168.77.10 verifier:192.168.77.40; do
  name=${spec%%:*}
  ip=${spec#*:}
  openssl req -newkey rsa:2048 -nodes -keyout "$name.key" -out "$name.csr" -subj "/CN=$name.northstar.test"
  printf 'subjectAltName=IP:%s,DNS:%s.northstar.test\nextendedKeyUsage=serverAuth\n' "$ip" "$name" > "$name.ext"
  openssl x509 -req -in "$name.csr" -CA ca.crt -CAkey ca.key -CAcreateserial -out "$name.crt" -days 90 -extfile "$name.ext"
done
echo 'Import ca.crt into the participant trust store. Keep ca.key offline with the organizer.'
