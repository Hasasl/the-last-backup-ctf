"""Deterministic 64 MiB FAT16 superfloppy, with one recoverable deleted entry.

Only the authoring tool uses this module. The filesystem begins at offset zero.
Short filenames keep deleted-entry recovery transparent in Sleuth Kit/Autopsy.
"""
import struct

SECTOR = 512
SECTORS = 131072
SPC = 4
FAT_SECTORS = 128
ROOT_ENTRIES = 512
ROOT_START = (1 + 2 * FAT_SECTORS) * SECTOR
DATA_START = ROOT_START + ROOT_ENTRIES * 32

def make_image(path, visible, deleted):
    image = bytearray(SECTORS * SECTOR)
    boot = image
    boot[:11] = b'\xeb\x3c\x90MSDOS5.0'
    struct.pack_into('<HBHBHHBHHHII', boot, 11,
                     SECTOR, SPC, 1, 2, ROOT_ENTRIES, 0, 0xF8,
                     FAT_SECTORS, 32, 64, 0, SECTORS)
    boot[36:39] = b'\x80\x00\x29'
    struct.pack_into('<I', boot, 39, 0x4E530217)
    boot[43:54] = b'NORTHSTAR  '
    boot[54:62] = b'FAT16   '
    boot[510:512] = b'\x55\xaa'
    fat = bytearray(FAT_SECTORS * SECTOR)
    struct.pack_into('<HH', fat, 0, 0xFFF8, 0xFFFF)
    cluster = 2
    metadata = []
    for index, (name, data, is_deleted) in enumerate(
        [(n, d, False) for n, d in visible.items()] + [(deleted[0], deleted[1], True)]
    ):
        data = data.encode('utf-8') if isinstance(data, str) else data
        stem, ext = name.split('.')
        if len(stem) > 8 or len(ext) > 3:
            raise ValueError('Use FAT 8.3 names')
        entry = bytearray(32)
        entry[:11] = (stem.upper().ljust(8) + ext.upper().ljust(3)).encode('ascii')
        entry[11] = 0x20
        # 2026-02-17 02:34:00; explicit UTC log fields are authoritative.
        struct.pack_into('<HH', entry, 22, (2 << 11) | (34 << 5), (46 << 9) | (2 << 5) | 17)
        struct.pack_into('<H', entry, 26, cluster)
        struct.pack_into('<I', entry, 28, len(data))
        count = max(1, (len(data) + SPC * SECTOR - 1) // (SPC * SECTOR))
        start = DATA_START + (cluster - 2) * SPC * SECTOR
        image[start:start + len(data)] = data
        if is_deleted:
            entry[0] = 0xE5  # Unlink directory entry, free FAT chain, preserve bytes.
        else:
            for c in range(cluster, cluster + count):
                struct.pack_into('<H', fat, c * 2, c + 1 if c < cluster + count - 1 else 0xFFFF)
        offset = ROOT_START + index * 32
        image[offset:offset + 32] = entry
        metadata.append(dict(name=name, deleted=is_deleted, cluster=cluster, size=len(data),
                             directory_offset=offset, data_offset=start))
        cluster += count
    image[SECTOR:SECTOR + len(fat)] = fat
    image[SECTOR + len(fat):SECTOR + 2 * len(fat)] = fat
    path.write_bytes(image)
    return metadata
