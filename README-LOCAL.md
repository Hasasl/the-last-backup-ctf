# Run The Last Backup locally

**v4: reset/replay buttons, lifetime profile counters and server-side guessing limits.** Sign in and choose **Replay**. Read [the player/reset guide](docs/REPLAY-AND-PROTECTION.md) and [the v4 test results](V4-TEST-REPORT.md). Use this folder's startup file to keep the update active.


Open Docker Desktop, then double-click **Start Full Project.cmd** in this folder.

Start playing at [http://localhost:8001](http://localhost:8001). Register a new player account. Stages unlock in order. Six challenges total 1,150 points.

| Service | Link |
|---|---|
| CTFd | http://localhost:8001 |
| OSINT archive | http://localhost:8081 |
| Web evidence portal | http://localhost:8083 |
| Final verifier (HTTP) | http://localhost:8443 |
| Linux SSH | 127.0.0.1:2222 |

See **LOCAL-ACCESS.txt** for the private organizer login, demo verifier token and exact SSH command. Give players only the relevant handouts and authorized access. Keep this folder private: it includes organizer solutions and backups.

After Stage 4, the organizer releases `build/handouts/northstar_evidence.img`. After Stage 5, the organizer releases SSH credentials and a verifier token. The local demo credentials are ready for your own testing.

Stop or start only the `last-backup-full` project in Docker Desktop. Do not delete its volumes if you want to retain scores. The original Stage 1 project remains separate at localhost:8000 and localhost:18081.

This copy uses localhost Docker containers, not four separate VMs. Its database and cache are not published. All web links use HTTP; access is limited to this PC.

Read **FULL-TEST-REPORT.md** for executed results and remaining classroom validation. Tests, helper scripts, evidence and image IDs are retained in this folder.

## New visual design

The Northstar theme is included and activated by the startup file. See `UI-UPDATE.md` for the design changes and current browser/regression checks.

## Reset the box

Double-click **Reset Box.cmd** (or run `local\reset.ps1` in PowerShell) with one of these options. Every reset prints what it changed and then checks the result.

| Command | What it resets | What is kept |
|---|---|---|
| `-Status` | Nothing. Shows containers and the health of all five player-facing services. | Everything |
| `-Linux` | Linux evidence container: evidence rebuilt from the read-only tar, analyst scratch folder wiped. | SSH host key, player accounts, scores |
| `-Portal` | Every player's Stage 3 review session (new `PORTAL_SECRET`, portal recreated). | Everything else |
| `-Verifier` | Verifier completions, attempts and sign-in throttle for **all** teams. Add `-Team team-01` for one team. | Teams and their tokens |
| `-Scores` | CTFd solves, wrong attempts, awards and hint purchases. | Player accounts, challenges, flags, hints |
| `-Players` | `-Scores` plus every non-admin player account. | Admin, challenges, flags, hints |
| `-All` | `-Linux -Portal -Verifier -Scores` in one go: a clean slate for the next session. | Player accounts |
| `-FullWipe` | **Everything**: all Docker volumes are deleted and the box is rebuilt. Issues a new demo verifier token and refreshes `local/private/known_hosts`. | Only the files in this folder |
| `-Backup` | Nothing. Saves CTFd SQL, uploads and verifier SQLite to `backups\<time>`. | Everything |

Add `-DryRun` to `-Scores`, `-Players` or `-Verifier` to see what would be deleted without deleting it. Destructive resets (`-Scores`, `-Players`, `-All`, `-FullWipe`) take an automatic backup first and ask for confirmation; use `-Yes` to skip the question and `-NoBackup` to skip the backup.

```powershell
.\local\reset.ps1 -Status
.\local\reset.ps1 -Verifier -Team team-01
.\local\reset.ps1 -Scores -DryRun
.\local\reset.ps1 -All
.\local\reset.ps1 -FullWipe
```

Backups and `local\private` contain password hashes, flags and keys. Keep them private. Full details, including how each stage is reset, are in `docs/RESET.md`. Automated checks: `python -m pytest tests/test_reset.py` (no Docker needed) and `python local/test_reset.py` (live, with the box running).
