# The Last Backup — Full Local Test Report

**UI update:** The player interface was redesigned and visually verified afterward. See [UI-UPDATE.md](UI-UPDATE.md) for current screenshots and regression results.

Verified: 10 October 2026, 01:11 Asia/Colombo.

**Result: the full six-stage baseline is running in Docker on this PC.** Seven long-running containers are healthy/running. The original Stage 1 setup is still available separately and its data was not modified.

**21 automated tests passed, plus 131 live/operational checks passed** (65 CTFd checks, 31 HTTP/evidence checks, 34 operations checks, and one Sleuth Kit recovery acceptance check). The last health sweep also returned HTTP 200 for all four full-project pages and both original Stage 1 pages. There are no unresolved failures among these executed checks. This is not a claim of four-VM acceptance or an independent blind solve.

## Open the project

| Service | Local address |
|---|---|
| Full CTFd | [http://localhost:8001](http://localhost:8001) |
| Stage 1 archive | [http://localhost:8081](http://localhost:8081) |
| Stage 3 portal | [http://localhost:8083](http://localhost:8083) |
| Stage 6 verifier — HTTP | [http://localhost:8443](http://localhost:8443) |
| Linux SSH | `analyst@127.0.0.1`, port `2222` |

Register a player account in CTFd. Organizer credentials, the local demo verifier token and SSH instructions are in [LOCAL-ACCESS.txt](LOCAL-ACCESS.txt). Keep that file private. Start the stack later with [Start Full Project.cmd](Start%20Full%20Project.cmd), after opening Docker Desktop.

## Scope and stage outcomes

| Stage | Executed verification | Result |
|---|---|---|
| 1 — OSINT | Corroborated notice, unique record matching, flag scoring, private paths unavailable | Passed |
| 2 — Steganography | Downloaded original PNG over HTTP; extracted the flag and next-stage clue | Passed |
| 3 — Web evidence | Wrong pair and missing CSRF rejected; correct pair releases flag and two files; second session stays locked | Passed |
| 4 — Cryptography | Downloaded ciphertext decrypts; recovered image hash matches the forensic image | Passed |
| 5 — Forensics | Deleted handover and timeline recovered; trusted manifest checksum matches Stage 6; Sleuth Kit independently recovered exact note | Passed |
| 6 — Linux investigation | Real SSH login, evidence permissions, scratch storage, genuine route checksum and final verifier | Passed |

The event has **six scored challenges worth 1,150 points**. All twelve hints cost **195 points**, leaving **955 points** when all are purchased. Stage 5A/5B is an optional source configuration; it was not activated in this event. Both importer configurations have automated coverage, but live CTFd acceptance here covers only the six-stage baseline.

Stage 3 is an authorization/evidence-analysis exercise. Stage 6 tests Linux evidence, permissions and integrity. Neither is an implemented host privilege-escalation exploit. The storyline verifies a recovery route; it does not restore a real backup.

## Platform and persistence

- CTFd 3.7.7, MariaDB 10.11 and Redis 7.4; archive uses Nginx 1.28.0. Container image IDs are recorded in `test-results/operations.json`.
- Docker Desktop 4.89.0, Docker Engine 29.7.2 on Windows. Application image uses Python 3.12.11; the SSH image uses Ubuntu 24.04.
- All five published ports bind to `127.0.0.1`. MariaDB and Redis have no published ports.
- Local web services use HTTP, including port 8443. HTTPS and certificate trust from the four-VM design are not exercised here.
- Each challenge uses a separate Docker bridge; the scoring database uses an internal network. The local bridges allow outbound access. This local run does not establish offline or four-VM network isolation.
- A whole-stack restart preserved CTFd accounts, solves, hint purchases and scores, plus verifier completion/attempt records. The Linux scratch directory reset and evidence remained intact. The stored SSH host key continued to validate.
- The live SQL backup was imported into a separate temporary database. Row counts and complete row contents matched for users, challenges, flags, hints, submissions, unlocks and pages. Only the temporary validation database was removed afterward; the backup is retained privately.
- A consistent verifier SQLite backup passed `integrity_check` and retained the completed test team and demo credential record. CTFd uploads were archived, but a full separate-host restore with populated uploads was not tested.
- Automated validation accounts are hidden from the public scoreboard and retained as evidence. The demo verifier team is separate and unsolved.

## Performance

Four concurrent clients made 16 ordinary-page requests across the four web services. All returned HTTP 200. The slowest was **2.125 seconds**, below the proposed three-second target. This is a small local concurrency check, not a capacity benchmark or four simultaneous end-to-end solves. Windows localhost IPv6 fallback contributes to these timings.

## Sleuth Kit acceptance

PASS: Sleuth Kit recovered deleted handover at metadata address 8; bytes match; original image unchanged.

Tool version: The Sleuth Kit ver 4.12.1. The evidence image was mounted read-only. File listing, recovered bytes and before/after SHA-256 records are retained in `test-results/sleuthkit-*` and `test-results/image-hash-*`.

## Issues resolved during this run

The original VM-specific addresses were replaced by loopback ports in a separate local Compose file. Docker Desktop did not publish ports on the original internal-only networks, so the local services use separate loopback-facing bridges. Verifier storage is initialized with the application user’s ownership. Windows bind-mount permissions were incompatible with SSH authorized-key checks; the key is now copied to a correctly permissioned runtime file before SSH starts. Local key generation quoting was corrected. Initial test harness failures (temporary-folder access, session-cache clearing, API-response assumptions and anti-bruteforce pacing) were corrected before the successful final runs.

Four deprecation warnings remain in the passing Python suite, from PyFatFS's filesystem dependencies. They are recorded in the suite output and do not fail the current pinned environment.

## Not run / remaining classroom acceptance

- Four separate Ubuntu VMs, their firewalls, offline restrictions and service-to-service isolation.
- HTTPS certificate validation.
- Independent non-author blind solve and usability feedback.
- Visual browser inspection/screenshots: the browser automation process failed to initialize; live HTTP/form/API tests were completed instead.
- A full separate-host disaster restore with populated CTFd uploads.
- Live seven-challenge Stage 5A/5B configuration.

Later-stage handovers remain organizer-controlled as specified by the implementation. After Stage 4, issue only `build/handouts/northstar_evidence.img`. After Stage 5, provide authorized SSH access and a verifier token. CTFd prerequisites do not automatically gate a separately hosted service or local file. The demo credentials in the private access file are for organizer demonstration.

## Detailed executed checks

### Automated suite — 21 passed

| Test | Result |
|---|---|
| `test_cipher_convention` | Passed |
| `test_osint_unique` | Passed |
| `test_image_note` | Passed |
| `test_integrity_chain` | Passed |
| `test_fat_independent_library` | Passed |
| `test_tar_link_permissions_no_flag` | Passed |
| `test_build_reproducible` | Passed |
| `test_portal_gates_all_attachments` | Passed |
| `test_portal_right_pair_and_session_isolation` | Passed |
| `test_portal_denied_event_not_proof` | Passed |
| `test_audit_filter_and_headers` | Passed |
| `test_verifier_anonymous_and_bad_token` | Passed |
| `test_verifier_generic_failure` | Passed |
| `test_verifier_correct_trim_and_persistence` | Passed |
| `test_rate_limit_persists_and_is_per_team` | Passed |
| `test_concurrent_attempt_limit` | Passed |
| `test_revoked_team_session_denied` | Passed |
| `test_login_rate_limit` | Passed |
| `test_ctfd_seed_order_and_score[challenges.json-6]` | Passed |
| `test_ctfd_seed_order_and_score[challenges-split5.json-7]` | Passed |
| `test_deployment_no_database_ports` | Passed |

### Live CTFd — 65 passed

| Check | Result |
|---|---|
| Player registration through HTTP | Passed |
| Six challenges and 1150 available points | Passed |
| Player cannot access admin configuration API | Passed |
| Final challenge locked before prerequisites | Passed |
| Correct final flag cannot bypass prerequisites | Passed |
| Stage 1: unlocked after preceding solve | Passed |
| Stage 1: wrong flag rejected | Passed |
| Stage 1: flag case enforced | Passed |
| Stage 1: correct flag accepted | Passed |
| Stage 1: duplicate does not score | Passed |
| Stage 1: hint 1 purchase | Passed |
| Stage 1: hint 1 content visible | Passed |
| Stage 1: hint 2 purchase | Passed |
| Stage 1: hint 2 content visible | Passed |
| Stage 1: cumulative score and hint charges | Passed |
| Stage 2: unlocked after preceding solve | Passed |
| Stage 2: wrong flag rejected | Passed |
| Stage 2: flag case enforced | Passed |
| Stage 2: correct flag accepted | Passed |
| Stage 2: duplicate does not score | Passed |
| Stage 2: hint 3 purchase | Passed |
| Stage 2: hint 3 content visible | Passed |
| Stage 2: hint 4 purchase | Passed |
| Stage 2: hint 4 content visible | Passed |
| Stage 2: cumulative score and hint charges | Passed |
| Stage 3: unlocked after preceding solve | Passed |
| Stage 3: wrong flag rejected | Passed |
| Stage 3: flag case enforced | Passed |
| Stage 3: correct flag accepted | Passed |
| Stage 3: duplicate does not score | Passed |
| Stage 3: hint 5 purchase | Passed |
| Stage 3: hint 5 content visible | Passed |
| Stage 3: hint 6 purchase | Passed |
| Stage 3: hint 6 content visible | Passed |
| Stage 3: cumulative score and hint charges | Passed |
| Stage 4: unlocked after preceding solve | Passed |
| Stage 4: wrong flag rejected | Passed |
| Stage 4: flag case enforced | Passed |
| Stage 4: correct flag accepted | Passed |
| Stage 4: duplicate does not score | Passed |
| Stage 4: hint 7 purchase | Passed |
| Stage 4: hint 7 content visible | Passed |
| Stage 4: hint 8 purchase | Passed |
| Stage 4: hint 8 content visible | Passed |
| Stage 4: cumulative score and hint charges | Passed |
| Stage 5: unlocked after preceding solve | Passed |
| Stage 5: wrong flag rejected | Passed |
| Stage 5: flag case enforced | Passed |
| Stage 5: correct flag accepted | Passed |
| Stage 5: duplicate does not score | Passed |
| Stage 5: hint 9 purchase | Passed |
| Stage 5: hint 9 content visible | Passed |
| Stage 5: hint 10 purchase | Passed |
| Stage 5: hint 10 content visible | Passed |
| Stage 5: cumulative score and hint charges | Passed |
| Stage 6: unlocked after preceding solve | Passed |
| Stage 6: wrong flag rejected | Passed |
| Stage 6: flag case enforced | Passed |
| Stage 6: correct flag accepted | Passed |
| Stage 6: duplicate does not score | Passed |
| Stage 6: hint 11 purchase | Passed |
| Stage 6: hint 11 content visible | Passed |
| Stage 6: hint 12 purchase | Passed |
| Stage 6: hint 12 content visible | Passed |
| Stage 6: cumulative score and hint charges | Passed |

### HTTP and evidence — 31 passed

| Check | Result |
|---|---|
| CTFd homepage responds | Passed |
| OSINT unique corroborated notice serves Stage 1 flag | Passed |
| Archive rejects /private/challenge.json | Passed |
| Archive rejects /build/organizer/challenges.json | Passed |
| Archive rejects /northstar_evidence.img | Passed |
| Archive rejects /.env | Passed |
| Original PNG downloadable | Passed |
| Stage 2 payload recovered from HTTP download | Passed |
| Stage 3 early attachment denied | Passed |
| Stage 3 health | Passed |
| Portal security headers | Passed |
| Portal missing CSRF rejected | Passed |
| Portal wrong evidence rejected | Passed |
| Correct evidence releases Stage 3 flag | Passed |
| Independent session remains locked | Passed |
| Cipher handover released | Passed |
| Training memo released | Passed |
| Stage 4 cipher solves | Passed |
| Stage 4 checksum matches Stage 5 image | Passed |
| Stage 5 deleted note recovered | Passed |
| Stage 5 timeline correct | Passed |
| Stage 5 manifest checksum matches Stage 6 | Passed |
| Verifier responds | Passed |
| Verifier rejects invalid token | Passed |
| Verifier token login | Passed |
| Verifier wrong answer rejected | Passed |
| Verifier correct answer returns final flag | Passed |
| Verifier completion survives another request | Passed |
| Deployed verifier enforces five attempts per minute | Passed |
| Four concurrent clients: all 16 pages succeed | Passed |
| Four concurrent clients: every page under three seconds | Passed |

### Operations — 34 passed

| Check | Result |
|---|---|
| Live CTFd SQL backup created | Passed |
| Restored SQL table matches: users | Passed |
| Restored SQL table matches: challenges | Passed |
| Restored SQL table matches: flags | Passed |
| Restored SQL table matches: hints | Passed |
| Restored SQL table matches: submissions | Passed |
| Restored SQL table matches: unlocks | Passed |
| Restored SQL table matches: pages | Passed |
| Restored SQL rows match: users | Passed |
| Restored SQL rows match: challenges | Passed |
| Restored SQL rows match: flags | Passed |
| Restored SQL rows match: hints | Passed |
| Restored SQL rows match: submissions | Passed |
| Restored SQL rows match: unlocks | Passed |
| Restored SQL rows match: pages | Passed |
| Verifier backup integrity | Passed |
| Verifier backup retains completed test team | Passed |
| Verifier backup retains demo token record | Passed |
| CTFd uploads archive saved | Passed |
| Port 8001 healthy after restart | Passed |
| Port 8081 healthy after restart | Passed |
| Port 8083 healthy after restart | Passed |
| Port 8443 healthy after restart | Passed |
| CTFd accounts, solves, hint purchases and scores survive restart | Passed |
| Verifier completion and attempt history survive restart | Passed |
| Linux scratch resets | Passed |
| Linux evidence readable | Passed |
| Linux evidence remains read-only | Passed |
| Linux scratch writable | Passed |
| Analyst has no sudo binary | Passed |
| Trusted route checksum verified through real SSH | Passed |
| Exactly five player-facing ports | Passed |
| All published ports bound to loopback only | Passed |
| Database and Redis not published | Passed |

## Evidence files

- `test-results/pytest.xml`: automated test outcomes.
- `test-results/ctfd-live.json`: live challenge and scoring results.
- `test-results/live-http.json`: web/evidence outcomes and individual timings.
- `test-results/operations.json`: restart, backup, bindings and image identifiers.
- `test-results/ssh.log` and `ssh-after-restart.log`: actual SSH results.
- `test-results/final-health.json`: final URL checks.
- `local/private/backup-validation/`: private SQL, SQLite and uploads backups.

The original Stage 1 project is kept separately. This separately runnable full-project copy is the folder containing this report.

## Reset mechanism (added after the first test run)

Implemented in `local/reset.ps1` with `local/reset_ctfd.py` and `local/reset_verifier.py`; documented in `docs/RESET.md`. This section records what has and has not been executed.

| Check | How | Status |
|---|---|---|
| Verifier reset: one team, all teams, dry run, repeat run, tokens kept | `tests/test_reset.py`, run offline against a database created by the real verifier code | Passed |
| Reset scripts are ASCII, compile and expose every documented switch | `tests/test_reset.py` | Passed |
| README documents every reset switch; no machine-specific paths remain | `tests/test_reset.py` | Passed |
| Linux scratch wiped and evidence rebuilt by `-Linux` | `python local/test_reset.py` | Not yet run on the live box |
| Verifier reset of one team on the live box, other teams untouched | `python local/test_reset.py` | Not yet run on the live box |
| Portal secret rotation and health on the live box | `python local/test_reset.py` | Not yet run on the live box |
| CTFd `-Scores -DryRun` leaves state unchanged | `python local/test_reset.py` | Not yet run on the live box |
| CTFd `-Scores` / `-Players` deletion and `-FullWipe` rebuild | Manual, on a disposable copy | Not yet run |

The live checks need Docker Desktop and the running stack. Run `python local/test_reset.py` and a manual `-All` / `-FullWipe` on a disposable copy before recording the demonstration, then update this table with the real results.
