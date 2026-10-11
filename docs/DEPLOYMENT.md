# Four-VM lab deployment

These steps implement the supplied architecture on disposable Ubuntu Server 24.04 VMs. Commands run from the `last-backup` project directory unless stated otherwise. Docker Engine and Compose must be installed before the offline classroom session. This guide is a deployment procedure, not evidence that the VMs have already been deployed.

## 1. Prepare VirtualBox

Create an **Internal Network** named `northstar-lab`, with these static addresses and no default gateway on that interface:

| VM | Address | vCPU | RAM | Disk | Player ports |
|---|---|---:|---:|---:|---|
| Control | 192.168.77.10/24 | 2 | 3 GB | 20 GB | TCP 443 |
| Challenge | 192.168.77.20/24 | 2 | 2 GB | 15 GB | TCP 8081, 8083 |
| Linux | 192.168.77.30/24 | 1 | 2 GB | 15 GB | TCP 22 |
| Verifier | 192.168.77.40/24 | 1 | 1 GB | 10 GB | TCP 443 |
| Participant | 192.168.77.100/24 | as available | 2+ GB | 20+ GB | client only |

Use VirtualBox consoles for host administration. Temporary NAT adapters may be used for dependency downloads, then **remove them before play**. Do not bridge to a campus/public network. Disable shared clipboard, drag-and-drop and shared host folders. Ensure no conflicting host service already binds the listed VM address/port. In particular, move or stop Ubuntu's host SSH listener on the Linux VM using its console before binding the challenge SSH container to port 22.

## 2. Build a frozen release

On the organizer build machine:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python build.py --portal-url http://192.168.77.20:8083
.venv/bin/python -m pytest -q
.venv/bin/python scripts/init_deploy.py
sh scripts/create_certs.sh
```

`init_deploy.py` refuses to overwrite `.env`. Keep it and the CA private key with the organizer. Copy only `ca.crt` to the participant trust store. On Ubuntu, copy it to `/usr/local/share/ca-certificates/northstar.crt` and run `sudo update-ca-certificates`; configure the browser trust store if it uses a separate one. Verify certificate SAN addresses match the VM URLs; do not disable certificate verification.

Distribute only the necessary pieces to each VM:

| VM | Required files |
|---|---|
| Control | `compose.control.yml`, relevant `.env` values, `deploy/nginx/control.conf`, its server certificate/key |
| Challenge | `compose.challenge.yml`, Dockerfile, `.dockerignore`, requirements, `ctf/`, `manage.py`, `build/stage1/`, `build/portal/`, archive/portal Nginx files, portal secret |
| Linux | `compose.linux.yml`, `deploy/linux/`, `build/organizer/linux-evidence.tar`, authorized public keys |
| Verifier | `compose.verifier.yml`, Dockerfile, `.dockerignore`, requirements, `ctf/`, `manage.py`, `build/verifier/`, verifier Nginx file and certificate/key, verifier secret |

Keep the directory structure. Do not copy organizer solution material onto the player filesystem. The Linux evidence tar deliberately excludes final flags and verifier answers.

## 3. Prepare runtime storage and SSH access

On the Verifier VM:

```sh
mkdir -p runtime/verifier-state
sudo chown 10001:10001 runtime/verifier-state
```

On each participant machine, generate an exercise-only key with `ssh-keygen -t ed25519`. Keep its private key on that participant. On the Linux VM, create `runtime/analyst_authorized_keys` containing eligible participant **public** keys, one per line; give it mode 644 and keep its parent organizer-controlled. Do not enable a participant key before Stage 5 is completed. An organizer test public key can be used for initial acceptance testing.

The baseline is one shared analyst evidence environment for a team of up to four. For simultaneous independent teams, clone the Linux VM per team or accept a shared read-only investigation space with a shared scratch directory. The verifier already supports separate team tokens and limits. SSH credentials and CTFd accounts are separate.

## 4. Start the correct stack on each VM

```sh
# Control VM only
docker compose -f compose.control.yml up -d
# Challenge VM only
docker compose -f compose.challenge.yml up -d --build
# Linux VM only
docker compose -f compose.linux.yml up -d --build
# Verifier VM only
docker compose -f compose.verifier.yml up -d --build
```

Pull/build while temporary setup Internet access is available. Each runtime Docker network is `internal: true`; there is no published database, Redis or application-worker port. Services are published only on their specified lab VM address. Keep host firewall input restricted to the table above and account for Docker's forwarding rules when configuring host firewalls; do not assume UFW alone controls published Docker ports. Disable routing between the classroom network and other networks. Use the participant and service-to-service checks in VALIDATION.md before admission.

Inspect `docker compose -f <file> ps` and `logs`. Record actual versions and image digests. The Compose files use a known CTFd 3.7.7 baseline, Python 3.12 and the proposed stack; they are not a claim that these tags are the newest versions.

## 5. Configure CTFd

Open `https://192.168.77.10`, complete initial organizer setup, select Teams mode if appropriate, and create a private administrator API token. On the organizer machine that trusts the classroom CA:

```sh
export CTFD_TOKEN='paste-admin-token-here'
.venv/bin/python scripts/seed_ctfd.py --url https://192.168.77.10
unset CTFD_TOKEN
```

If Python does not automatically use the updated system CA, set `SSL_CERT_FILE` to the trusted CA bundle. Do not use an insecure bypass. The seed tool creates hidden standard challenges, flags and paid hints; assigns a chain of prerequisites; then makes them visible. It refuses duplicate challenge names. If a request fails, inspect and remove only that interrupted new event's partial records before rerunning, or complete them manually. It does not delete existing data.

Use `--split-stage5` only for a **new event** if the group approves seven scored challenges. Both configurations total 1,150 points. Verify hint charges, duplicate-solve scoring, prerequisites and exact flag handling using non-admin player accounts. The importer has unit coverage but has not been run against a live CTFd server in this build environment.

## 6. Release handovers

1. Stage 1 website is the public entry. Stage 2 gets the original image from it.
2. Stage 3 releases its ciphertext and memo only after a correct evidence review in the same browser session.
3. After checking the team's Stage 4 solve in CTFd, give it **only** `build/handouts/northstar_evidence.img` through an organizer-controlled private transfer. Do not put the image in a public web root. Its plaintext checksum validates the transfer.
4. After the Stage 5 solve (and 5B if selected), enable the team's public key, issue a verifier token, and give the player the SSH address and console URL.

On the Verifier VM, after the service has initialized its database:

```sh
docker compose -f compose.verifier.yml exec verifier python manage.py issue-team team-01 --database /state/verifier.sqlite
```

Store the printed token privately and hand it to that team. Use `--rotate` to replace the token; `revoke-team team-01 --database /state/verifier.sqlite` disables new requests from existing sessions too. Rotation changes the login token but does not clear active sessions or progress. All submissions share a five-per-minute allowance per team, stored transactionally in SQLite across workers/restarts.

The browser's verifier session is HTTPS-only in deployment. The portal intentionally uses isolated-lab HTTP, matching the design. Tokens are submitted in form bodies, never in URLs. Nginx uses a fixed single-proxy path; login throttling uses that proxy's address and therefore conservatively shares a ten-per-minute sign-in cap across teams. Answer throttling is independently per team.

## 7. Reset and backup

Redeploy the same immutable build to reset the archive and portal. Restart the Linux container to restore its evidence and clear scratch space; preserve its SSH host-key volume. Do not run `down -v` on the Control stack during play. Do not delete verifier state during an active event. Existing completed portal cookies may remain valid across a service restart; change only the portal secret for a new event when you intentionally want all review sessions invalidated.

Use `sh scripts/backup_control.sh` on the Control VM to quiesce the frontend, back up MariaDB and uploads, then restart it. Back up `.env`, certificates and the release register separately. On the Verifier VM, stop its service, copy `runtime/verifier-state` including any SQLite WAL/SHM files, then restart it. Never claim recovery is validated before restoring a copy into a disposable lab.

Restore Control data only into a separate disposable stack first: stop its CTFd/frontend, import `ctfd.sql` with `docker compose exec -T database mariadb ...` using the container's configured credentials, and extract `uploads.tar` into its uploads volume using a one-off CTFd container. Reuse the matching secrets and release. Verify accounts, uploads, scores and hint purchases, then retain the clean VM snapshots. Take a final clean lab snapshot after the acceptance checklist passes.


### Local Docker deployment

The single-PC Docker version (`compose.local.yml`) has a one-command reset tool, `local/reset.ps1` (**Reset Box.cmd**), with per-component resets, a dry-run mode, automatic backups and verification. See `docs/RESET.md`. The commands above remain the procedure for the four-VM lab.
