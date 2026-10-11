# v4 replay and guessing protection — executed validation

Date: 11 October 2026, Asia/Colombo. Source: the supplied v3 ZIP. Target: original Docker/CTFd project, not Vercel.

## Results

| Validation | Result |
|---|---|
| Local Python regression suite | **35 passed**, 0 failed; four dependency deprecation warnings |
| Isolated CTFd 3.7.7 / MariaDB / Redis HTTP suite | **57 checks passed**, 0 failed |
| Before/after original event preservation | **12 comparisons passed** |
| Updated live HTTP health | CTFd, archive, portal and verifier all HTTP 200 |
| Browser validation | Wrong/correct counters, completed-run disabling, stage reset, reset cancellation, bulk reset and profile totals verified |

The 57 HTTP checks include repeated statistics requests and five individual later-stage solves; they are checks, not 57 independent test cases. Full results: [replay-live.json](test-results/replay-live.json).

## Behaviors verified

- Real sign-in and required CSRF tokens; anonymous reset denied.
- Unsolved practice and prerequisite-locked competition stages denied.
- Wrong/correct competition flags imported into lifetime history exactly once.
- Wrong/correct practice results; duplicate completed-run submission rejected.
- Reset then solve the same stage again; lifetime totals retained.
- No duplicate scoring solve; all six competition stages still total 1,150 points.
- Independent player histories and denial of an attempted other-user reset.
- Shared allowance across ordinary flag submissions and practice.
- Five simultaneous accepted guesses out of ten concurrent requests; five HTTP 429 responses.
- Hourly cap after minute allowance expires; reset cannot refill flag allowance.
- Reset-spam cap and resistance to a forged forwarded-IP header.
- Bulk reset updates all six unlocked stages; GET requests do not change state.
- Malformed submissions rejected; repeated history import remains idempotent.
- Portal guessing remains limited after clearing browser cookies, including concurrent requests.
- Verifier hourly cap refuses a valid answer once allowance is exhausted.

The first concurrent run exposed a stale MariaDB transaction snapshot. The limiter now refreshes the session after acquiring its lock. The complete live suite passed after that fix. An initial test assumed an unsupported-method response must be 405; CTFd's fallback returns 404, so the final assertion checks refusal and unchanged counters instead.

## Browser evidence

The disposable player belonged only to the separate test event on port 8004. Its final browser view showed **7 correct, 1 wrong, 8 stage resets, 1 whole-practice reset**, with the competition score still **1,150**. Six of those correct flags came from the seeded browser fixture; one was submitted through the replay button. The automated suite separately verified the real six-stage scoring flow.

![Profile after replay and reset](test-results/screenshots/replay-profile.png)

The native popup confirmation caused a browser-control stall during validation. The final interface uses a visible on-page **Confirm reset / Cancel** control; both stage and whole-practice confirmation were then exercised successfully. Desktop browser validation was performed; no mobile screenshot validation was performed for this update.

## Original event preservation

The original event was backed up before activation to `backups/20261010T205201Z`. A second snapshot is in `backups/20261010T205410Z`.

SQL insert rows for users, teams, challenges, flags, hints, solves, fails, submissions, awards and unlocks matched exactly. Upload file hashes and all four verifier state tables also matched. Results: [upgrade-preservation.json](test-results/upgrade-preservation.json). No player fixture was created in the original event. The separate test containers were stopped after validation; the main project remains running on its original localhost ports.

The plugin adds three new MariaDB tables. The Stage 3 service adds a persistent limiter volume. Existing v3 files in Downloads and the supplied ZIP remain unchanged; Docker now mounts this v4 working folder.

## Scope and limits

Player controls reset practice state, not shared containers, flags or already downloaded evidence. Global organizer score/player/full-wipe actions were not executed against the original event. Team mode was not end-to-end tested. No online deployment, four-VM deployment test, external penetration test or distributed load test is claimed. The new limiter uses the existing localhost no-proxy configuration.

Old `FULL-TEST-REPORT.md` and `UI-UPDATE.md` describe earlier work; their historical test counts must not be combined with this update's results as a single new test run.

## Repeatable commands

Local tests: `python -m pytest tests -q` using the development dependencies.

For a disposable Docker test environment only:

```powershell
docker compose --env-file local/.env -f compose.replay-test.yml up -d
docker compose --env-file local/.env -f compose.replay-test.yml exec -T ctfd python /bootstrap/bootstrap_full.py
docker compose --env-file local/.env -f compose.replay-test.yml exec -T -e NORTHSTAR_TEST_ENV=isolated ctfd python /replay-tests/test_replay_live.py
docker compose --env-file local/.env -f compose.replay-test.yml stop
```

The test configuration uses its own project name, explicitly named volumes, signing key and port. Do not point these fixture tests at the real event. The browser-fixture helper was a one-time validation aid, not an installation step.
