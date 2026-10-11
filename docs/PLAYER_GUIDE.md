# The Last Backup — player briefing

Northstar Labs is about to trust a recovery route that someone changed. Maya left a trail before her account was disabled. Elias preserved a warning. Follow their evidence and identify the genuine route. All organizations, identities, records and backups in this exercise are fictional.

Submit each `FLAG{...}` completion code in CTFd. Flags are case-sensitive and are not passwords. Your organizer supplies the competition and service addresses. Paid hints reduce your score; the six-stage maximum is 1,150 points.

1. **The Missing Employee — OSINT, 100 points.** Compare the current directory with the preserved event register and older notices. Match both the case reference and UTC meeting time. Keep the original linked image.
2. **More Than a Photograph — Steganography, 100 points.** Download the original PNG without editing or resizing it. The handling note specifies its bit and byte convention. Recover the note and its approval reference.
3. **Someone Used Her Name — Web security, 200 points.** Read the role policy, transactions and audit API. Select the pair proving an accepted approval without the required permission. Correct review releases two files.
4. **The Administrator’s Warning — Cryptography, 200 points.** Apply the memo's repeating-key cipher precisely, including key alignment across lines. After scoring, request the forensic image and verify its checksum against the warning.
5. **Seventeen Missing Minutes — Digital forensics, 250 points.** Preserve the original and analyse a copy. It is a 64 MiB raw FAT16 filesystem beginning at offset zero, with no partition table. Recover deleted evidence and reconstruct the timeline. `AUDIT.JSL` contains one JSON object per line; its short filename accommodates FAT 8.3 entries. Keep the service identity, UTC interval and trusted manifest checksum.
6. **The Wrong Recovery Route — Linux security, 300 points.** After scoring Stage 5, obtain your analyst SSH access and separate verifier token. Read `/srv/northstar/README.txt`, inspect permissions, follow the pointer and investigate the logs. Authenticate the manifest before trusting its route checksum. Submit release ID, route ID, service and redirection event together to the verification console, then score the returned flag in CTFd.

Useful tools include a browser, Python/Pillow or a red-channel LSB tool, a text editor, SHA-256 utilities, Autopsy or Sleuth Kit, and standard Linux commands. Sleuth Kit can enumerate deleted entries with `fls -r -d northstar_evidence.img`; use the discovered metadata address with `icat -r` to recover the selected file. Never substitute an assumed metadata address.

Work only on the provided lab systems. Do not attack CTFd, the verifier infrastructure, classmates or outside systems. The final console verifies evidence; it does not execute commands or restore a real backup. If the organizer adopts the optional split, Stage 5A awards 100 points for recovery and Stage 5B awards 150 for the timeline; follow its explicit flag-construction rule in CTFd.
