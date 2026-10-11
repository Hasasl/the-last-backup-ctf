#!/bin/sh
set -eu
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends sleuthkit
fls -V > /results/sleuthkit-version.txt
sha256sum /evidence/northstar_evidence.img > /results/image-hash-before.txt
fls -r /evidence/northstar_evidence.img > /results/sleuthkit-files.txt
inode=$(awk '/\*.*ANDOVER.TXT/ {gsub(":", "", $3); print $3}' /results/sleuthkit-files.txt)
test -n "$inode"
icat -r /evidence/northstar_evidence.img "$inode" > /results/sleuthkit-recovered.txt
cmp /results/sleuthkit-recovered.txt /expected/recovered-handover.txt
sha256sum /evidence/northstar_evidence.img > /results/image-hash-after.txt
cmp /results/image-hash-before.txt /results/image-hash-after.txt
printf 'PASS: Sleuth Kit recovered deleted handover at metadata address %s; bytes match; original image unchanged.\n' "$inode" > /results/sleuthkit-result.txt
