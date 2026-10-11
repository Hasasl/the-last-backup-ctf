# Player replay, profile history and guessing protection — v4

This update targets the original localhost Docker deployment with CTFd 3.7.7 and MariaDB. It is separate from the Vercel work.

## How to use it

1. Open Docker Desktop and run **Start Full Project.cmd** from this v4 folder.
2. Sign in at http://localhost:8001 and solve a stage normally.
3. Choose **Replay** in the navigation, or **Replay stages / reset practice** in your profile.
4. Open the stage evidence and work through it again. Submit its flag on the replay page.
5. Players cannot reset anything. Resets are organizer-only (see RESET.md).
6. **Reset all my practice stages** restarts every unlocked practice stage in one action.
7. Your **Profile** shows lifetime correct flags, wrong flags, stage resets and whole-practice resets, plus a breakdown for each solved stage.

A correct practice submission completes that run. To count another correct solve, first reset that stage. Repeated submission on an already completed run is rejected and does not increase the correct counter. Competition scoring remains one solve per stage, at most 1,150 points before hint deductions. Practice earns no extra points and does not change hint purchases or unlock prerequisites.

## What a player reset actually resets

The player buttons reset personal **practice progress**, not the shared Docker machine. They clear a practice stage's completed marker and advance its run number. They keep competition solves, points, hints, lifetime history, other players' records and all guessing limits. A whole-practice reset adds one whole-reset event plus one stage-reset event for each affected stage.

The six stages still use the same evidence and flags. These buttons do not generate new secrets, erase downloaded evidence, clear the portal cookie, remove a team's verifier completion, or wipe the shared Linux scratch directory. Players may remember previously found flags. This is repeatable practice, not proof that they solved the puzzle from scratch each time.

The original organizer **Reset Box.cmd** and `local/reset.ps1` remain the controls for actual shared-service recovery. `-Linux` wipes shared scratch and rebuilds evidence; `-Portal` invalidates all review cookies; `-Verifier -Team <id>` clears that verifier team's completion. These are organizer operations because those resources are shared. See [RESET.md](RESET.md).

`-Scores` retains the new lifetime ledger while clearing competition progress. `-Players` deletes the removed users' history too. `-FullWipe` deletes all database volumes, including history and limits. Backups are therefore still essential for organizer wipes. Practice resets require neither a global wipe nor a container restart.

## Counter definitions and persistence

- **Correct flags:** stored CTFd correct submissions plus evaluated correct practice flags.
- **Wrong flags:** stored CTFd incorrect submissions plus evaluated wrong practice flags.
- **Stage resets:** each explicit per-stage reset, including stages affected by a whole-practice reset.
- **Whole practice resets:** number of successful bulk-reset actions.

Blocked, malformed, unauthenticated, locked-stage and duplicate-completed-run requests do not become flag-result events. The request limiter can still count these requests to discourage abuse. Historical CTFd rows are imported once by their submission ID; previously deleted v3 history cannot be reconstructed. Legacy CTFd rows labeled incorrect are imported as wrong, including any older throttle-generated incorrect rows.

Profiles show these statistics only to the signed-in owner. In team mode, competition access and limits follow the shared team account, while practice results and resets belong to the individual user. The executed tests covered the project's default individual-player mode.

The `northstar_events`, `northstar_runs` and `northstar_limits` tables live in the existing MariaDB volume. Restarting CTFd, clearing Redis, logging out or pressing a practice reset does not clear those tables. Database backups include them. Raw practice flag guesses are not stored in this ledger.

## Guessing limits

| Input | Limits | Stored in |
|---|---|---|
| CTFd flag checks, competition + practice combined | 5 requests/minute and 30/hour per account; 60/minute and 300/hour per socket IP | MariaDB |
| Player reset actions | 3/minute and 20/hour per account; shared IP caps also apply | MariaDB |
| Stage 3 evidence form | 5/minute and 30/hour per socket IP | `portal-state` SQLite volume |
| Final verifier | 5/minute and 30/hour per team; existing login limit remains 10/minute per IP | `verifier-state` SQLite volume |

CTFd counters use fixed windows starting at the first request; portal/verifier use rolling windows. A CTFd throttle response is HTTP 429 with a `Retry-After` header and a readable message. All CTFd submissions, across stages and pages, share account buckets. Repeated requests during the cooldown do not extend it. Resets have their own allowance and cannot refill flag allowance.

MariaDB advisory locks and SQLite immediate transactions coordinate simultaneous requests across workers. CTFd reloads its transaction snapshot after acquiring the lock to avoid stale concurrent counters. The localhost stack keeps `REVERSE_PROXY=0`; arbitrary forwarding headers do not select a new IP bucket. Shared local addresses may share the IP allowance.

These controls mitigate online automated guessing. They cannot prevent someone using a flag already known, shared by another player or recovered from organizer files, nor can they prevent offline guessing of downloaded artifacts. The original static challenge flags are retained. This is not a distributed denial-of-service protection service.

## Installation and validation

The plugin is mounted from `local/plugins/northstar_replay` by `compose.local.yml`; `local/prepare.py` preserves that mount. Use the v4 startup file, not the old v3 shortcut. The plugin adds tables automatically; no existing CTFd submission is deleted by installation. The Northstar theme adds navigation, dashboard and profile components. The Stage 3 container now has a separate writable state volume for its persistent limiter; its evidence stays read-only.

Read [V4-TEST-REPORT.md](../V4-TEST-REPORT.md) for the executed results. The standalone test compose uses explicitly separate `last-backup-v4-test_*` volumes, a different signing key and port 8004. Its test script refuses to run without the explicit test-only environment flag. Never run that suite against a real event: it creates hidden test players and manipulates test rate-limit buckets.

Implementation reference: [CTFd 3.7.7 challenge API](https://github.com/CTFd/CTFd/blob/3.7.7/CTFd/api/v1/challenges.py). The plugin wraps the native attempt method so the existing prerequisite, visibility, event-time and scoring checks still apply.
