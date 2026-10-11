# Implementation validation

Test date: **25 September 2026**. Environment: Windows, Python 3.12, Flask 3.1.2, Pillow 11.3.0, Waitress 3.0.2. Executed by the implementation agent; these results are not an independent student blind solve.

## Executed checks

**21 automated tests passed.** Test source is in `tests/test_project.py`; machine-readable output is in `test-results/pytest.xml`. `test-results/installed-windows.txt` records the resolved local dependencies. PyFatFS's filesystem abstraction dependency emits deprecation warnings; the test environment pins the compatible setuptools version.

| Area | Verified result |
|---|---|
| OSINT | Exactly one notice matches the case and meeting timestamp |
| PNG | Independent extraction recovers the exact Stage 2 flag and approval reference |
| Cipher | Published fixture, case/punctuation handling, cross-line key alignment and round trip pass |
| Integrity | Decrypted image hash, image bytes, trusted manifest hash and route bytes agree |
| Forensics | Independent parser recovers the deleted note; PyFatFS mounts the image and reads live files, excluding the deleted entry |
| Timeline | Case/session correlation produces mn-sync, 02:17–02:34 UTC and the correct manifest hash |
| Linux package | Tar contains a real symlink, read-only evidence modes, and no CTF flags |
| Reproducibility | Repeated builds produce identical image, ciphertext, PNG and Linux tar bytes |
| Portal | Early downloads fail; wrong/denied evidence pairs fail; correct pair succeeds; sessions remain separate |
| Verifier | Authentication, CSRF, generic failure, exact/trimmed correct answer and persistent completion work |
| Attempt limits | Five attempts per team per minute, restart persistence, team separation and simultaneous-request enforcement pass |
| Credential controls | Invalid-token throttling and revocation of active sessions pass |
| CTFd importer | Mock API tests verify flags, hints, prerequisite sequencing and 1,150 points for both configurations |
| Deployment configuration | YAML parses; database, cache and CTFd worker ports are not published; runtime networks are internal |

Live local browser checks also completed: the archive renders; Stage 3 accepts TX-217/AUD-217 and displays both handover links; verifier sign-in and R17/EXIT-04/mn-sync/EVT-024 submission display the final success result. Local application requests use real Waitress HTTP servers. These checks do not exercise Nginx or HTTPS.

## Checks still required in the lab

Docker was not installed on the build computer. Do not present the following as passed until the four-VM lab has been tested:

- [ ] Build/pull containers and record image digests and installed Linux package versions.
- [ ] Validate Compose with `docker compose -f <file> config --quiet` on each intended VM.
- [ ] Confirm all services start and TLS certificates validate from the participant browser.
- [ ] Run the CTFd importer against a new event; verify accounts, exact flags, near misses, repeated solves, paid hints, prerequisites and permissions using a player account.
- [ ] Verify only the five intended service paths from the participant. Confirm MariaDB, Redis, worker listeners, host management ports and outbound Internet paths are inaccessible.
- [ ] Verify service-to-service isolation and Docker forwarding rules; the Compose configuration alone is not proof of host/network isolation.
- [ ] Log in with the analyst key; verify evidence is readable but cannot be modified, no sudo access is available, and scratch writes work.
- [ ] Recover the deleted note using **Sleuth Kit or Autopsy**, record the actual metadata address and tool version, and hash the output. The independent parser/PyFatFS checks are not a substitute for this tool-specific acceptance test.
- [ ] Restart the verifier and retest team limits/completion on the deployed database.
- [ ] Restore Control database/uploads and verifier state into disposable copies and verify scores, hints and accounts.
- [ ] Ask a non-author to solve all six stages without verbal help. Record duration, ambiguity and evidence references.
- [ ] Run four participant sessions together and measure ordinary-page response times against the proposed three-second target.

## Design limits recorded accurately

Static flags can be shared and the Stage 1 flag is searchable. Source/organizer access exposes answers by design, so only intended handouts go to players. Stage 3 is a supplied-record authorization analysis challenge, not a live privilege escalation exploit. The Linux stage tests evidence, permissions and integrity rather than exploitation of the host.

A PNG modification does **not necessarily** destroy an LSB payload: a lossless re-save or a crop outside the encoded region can preserve it. This implementation requires the original image and verifies its recovery; it does not claim that every transformed image fails cleanly. Hash the original to establish byte identity.

The default six-stage scope retains the approved baseline. Optional 5A/5B remains a documented alternative, not an assertion of lecturer/group approval. All dates, identities and data are fictional. No automatic backup restoration occurs.

## Evidence record template

For each remaining check retain: release ID, artifact SHA-256, tool/version, tester, UTC date, exact steps, expected result, actual result and screenshot or terminal evidence. Use `not run`, `passed` or `failed`; never replace a planned result with a claimed pass.
