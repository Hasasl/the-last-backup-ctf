# Reset and recovery

**Organizer reset (admin dashboard):** sign in to CTFd as admin, open **Plugins → Reset Challenges** (`/admin/northstar-reset`), type `RESET` and confirm. This clears solves, wrong attempts, submissions, hint unlocks and practice runs so every player is back at stage 1. Player accounts, teams, challenges, flags, hints, awards and each player's lifetime flag-check history are kept. Players have no reset controls; the endpoint rejects them. Linux scratch, portal sessions and the verifier are still reset with the commands below.

The box holds state in five places. Each stage has a reset, and `local/reset.ps1` (or **Reset Box.cmd**) runs them. This page explains what each reset does and why it is safe.

## Where state lives

| Stage / service | Port | State | Reset command | What the reset does |
|---|---|---|---|---|
| 1 OSINT archive | 8081 | None (static files mounted read-only) | none needed | Nothing to reset. A redeploy gives identical content. |
| 2 Steganography | 8081 / CTFd | Original PNG is a static file | none needed | Same as above. Handout checksums are in `build/organizer/release-register.json`. |
| 3 Web evidence portal | 8083 | Signed cookie in the player's browser | `-Portal` | Rotates `PORTAL_SECRET` in `local/.env` and recreates the portal container. Every existing review session becomes invalid. |
| 4 Cryptography | CTFd | Files only | none needed | Immutable build output. |
| 5 Forensics | handout | `northstar_evidence.img` is a static handout | none needed | Players work on their own copy. Verify with the checksum in the release register. |
| 6 Linux investigation + verifier | 2222 / 8443 | Linux scratch (tmpfs), verifier SQLite in the `verifier-state` volume | `-Linux`, `-Verifier` | `-Linux` restarts the container: evidence is re-extracted and scratch is wiped. `-Verifier` deletes completions, attempts and sign-in throttle rows. |
| Scoring | 8001 | MariaDB volume `ctfd-db`, uploads volume | `-Scores`, `-Players`, `-FullWipe` | See below. |

## Component details

**Linux (`-Linux`).** The evidence tar is mounted read-only; the entrypoint extracts it into a tmpfs and sets read-only permissions every start. `/home/analyst/work` is also tmpfs. A restart therefore restores the evidence and removes anything a player wrote. The SSH host key is in a separate volume and is kept, so players do not see a host-key warning. After the restart the script checks that the scratch folder is empty and that `/srv/northstar/routes/EXIT-04.route` exists.

**Portal (`-Portal`).** Review progress lives only in the signed session cookie, so the only server-side way to cancel it is to change the signing secret. The script writes a new random value into `local/.env` and recreates the container, then checks `/health`.

**Verifier (`-Verifier [-Team id]`).** Runs `local/reset_verifier.py` inside the verifier container. It deletes rows from `completions`, `attempts` and `logins` in one `BEGIN IMMEDIATE` transaction. The `teams` table is not touched, so issued tokens keep working. A team that was already signed in stays signed in but no longer sees the flag until it solves the verifier again. Use `-DryRun` first to see the row counts.

**CTFd (`-Scores`, `-Players`).** Runs `local/reset_ctfd.py` inside the CTFd container. `-Scores` deletes `solves`, `fails`, `submissions`, `awards`, `unlocks` (hint purchases) and `tracking`, then clears the CTFd cache so the scoreboard updates. Challenges, flags, hints, pages, theme and the admin account are never touched. `-Players` also deletes non-admin accounts and their dependent rows. After the delete the script checks that no progress rows remain and that challenges still exist.

**Full wipe (`-FullWipe`).** Runs `docker compose down -v --remove-orphans`, deletes `local/private/known_hosts`, runs `start.ps1` (rebuild, event bootstrap, theme), refreshes `known_hosts` from the new SSH host key, and issues a new token for the `demo` verifier team (saved in `LOCAL-ACCESS.txt`). The confirmation word is `RESET`.

## Recovery

`-Backup` writes `backups\<UTC time>\ctfd.sql`, `uploads\` and `verifier.sqlite`. The verifier copy uses SQLite's online backup API so it is consistent while the service runs. Destructive resets run this automatically first and refuse to continue if the backup fails.

To restore CTFd data after a mistake, restore into a throw-away database first (the same method used in `local/test_operations.py`): create a scratch database, import `ctfd.sql` with `mariadb`, and compare row counts and contents before replacing anything. To restore the verifier, stop the verifier container, copy `verifier.sqlite` over `/state/verifier.sqlite` in the `verifier-state` volume and start it again.

`scripts/backup_control.sh` is for the original four-VM deployment (`compose.control.yml`). For this local Docker setup use `-Backup`.

## Rules of thumb

- Use `-Linux` between attempts, `-Verifier -Team <id>` when one team needs a second go, `-All` between sessions and `-FullWipe` only to start a brand-new event.
- Do not run `-Scores`, `-Players` or `-FullWipe` during a live event.
- Run `-Status` after any reset. All five services should answer.
- If PowerShell blocks the script, use **Reset Box.cmd**; it starts PowerShell with the right execution policy.

## Tests

| Test | How to run | Needs Docker |
|---|---|---|
| Verifier reset (one team, all teams, dry run, repeatability), script safety, README/switch coverage | `python -m pytest tests/test_reset.py` | No |
| Linux scratch + evidence, verifier one-team reset, portal secret rotation, CTFd dry run | `python local/test_reset.py` (writes `test-results/reset-tests.json`) | Yes, box running |
