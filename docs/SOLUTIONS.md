# Organizer solution guide

**Private assessor material. Do not distribute to players.** Exact flags are in `build/organizer/challenges.json`, with the optional seven-challenge version alongside it.

## Stage 1

The current directory misstates Maya's case as MN06-0199. The preserved event register gives **MN06-0217, 2026-02-17 01:40 UTC**. Notice 062 matches both; 061 has the wrong case and 063 the wrong time. Notice 062 carries the first flag and original image link. Static searching can reveal this flag; assess the two corroborating facts as well.

## Stage 2

Read the red-channel LSB for each PNG pixel in row-major order. Assemble eight bits MSB first, stop at a zero byte, decode UTF-8. The recovered note supplies the second flag, APR-0217 and the portal URL. `scripts/solve.py png build/stage1/event-original.png` demonstrates recovery.

## Stage 3

The policy permits `backup-admin` to approve and denies `sync-agent`. **TX-217 + AUD-217** show that `mn-sync`, a sync-agent, had an approval accepted under Maya's label. AUD-219 records a denial and does not prove the bypass. TX-211 is an authorized administrator approval. Correct evidence releases flag 3, `elias.enc.txt` and `training-memo.txt`. Direct attachment requests without a reviewed session return 403.

## Stage 4

Decrypt using ORACLE, A=0, subtract key values modulo 26, preserve case and non-letters, advance only on ASCII letters continuously across newlines. The fixture `ABC abc!` ↔ `OSC cmg!` verifies the convention. Plaintext reveals flag 4, `northstar_evidence.img` and its computed SHA-256. The organizer copy of plaintext is private. Compare actual image bytes before release.

## Stage 5

Use Autopsy/Sleuth Kit to identify the deleted `_ANDOVER.TXT` entry and recover it. Its first filename byte is deleted; the original HANDOVER.TXT contents remain in unallocated contiguous clusters. The FAT chain is freed and no later writes overwrite those clusters. Do not hard-code a Sleuth Kit metadata address; enumerate the actual released image. The builder's private `fat-entries.json` describes offsets for engineering checks but is not the player workflow.

The recovered note contains flag 5 and directs correlation. `SESSION.LOG` links case MN06-0217 and session S-217 to service **mn-sync**, start **02:17**, end **02:34 UTC**, a 17-minute interval. `AUDIT.JSL` event **A-218** preserves the pre-change manifest under **REL-017**; use that record in `RELEASE.CSV` to obtain the trusted manifest hash. A-225 advertises a replacement and is not the preserved pre-change record. S-199 has the wrong case and S-218 the wrong session/service.

The optional Stage 5B flag is `FLAG{st05b_mn-sync_0217_0234}`. Its construction rule is supplied in that challenge's brief. In the default six-stage configuration, check the timeline and hash as viva evidence before releasing Linux access; there is no seventh scored challenge.

## Stage 6

`CURRENT_EXIT` is a real symlink pointing to **EXIT-09**, the misleading replacement. In the Linux shell:

```sh
id
cd /srv/northstar
ls -ld . routes manifests logs
ls -l CURRENT_EXIT
readlink CURRENT_EXIT
cat CURRENT_EXIT
cat logs/release.log logs/maintenance.log
sha256sum manifests/*.sha256
sha256sum -c manifests/R17.sha256
```

Only R17's manifest matches the trusted hash from Stage 5. It lists EXIT-04 and the actual route-file checksum. The maintenance log records mn-sync redirecting the pointer under **EVT-024 at 02:24 UTC**, within the recovered window. Submit **R17 / EXIT-04 / mn-sync / EVT-024** to the separate verifier. All four fields are needed; surrounding spaces are stripped and case is preserved. Wrong combinations get the same generic result. Correct evidence returns the final flag for CTFd submission.

The analyst should be able to read evidence but cannot write it or obtain sudo privileges. Their scratch directory is separate. The Linux image does not contain the final flag or the verifier answer configuration. The root filesystem and evidence are isolated from the verifier database. File hashes establish agreement with a preserved reference, not authorship by themselves.
