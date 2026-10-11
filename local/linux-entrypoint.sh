#!/bin/sh
set -eu
test -s /etc/ssh/authorized_keys/analyst
mkdir -p /run/sshd
if [ ! -s /hostkeys/ssh_host_ed25519_key ]; then
  ssh-keygen -q -t ed25519 -N '' -f /hostkeys/ssh_host_ed25519_key
fi
tar -xf /evidence.tar -C /srv/northstar
chown -R root:evidence /srv/northstar
find /srv/northstar -type d -exec chmod 750 {} +
find /srv/northstar -type f -exec chmod 440 {} +
chown analyst:evidence /home/analyst/work
chmod 700 /home/analyst/work
install -m 644 /etc/ssh/authorized_keys/analyst /run/analyst_authorized_keys
exec /usr/sbin/sshd -D -e -o AuthorizedKeysFile=/run/analyst_authorized_keys
