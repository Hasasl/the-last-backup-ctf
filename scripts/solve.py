"""Organizer reference solver. Never distribute this with the player files."""
import argparse
import csv
import hashlib
import io
import json
import struct
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ctf.cipher import transform

def extract_png(path):
    pic = Image.open(path).convert('RGB')
    result, byte = bytearray(), 0
    for index, (red, _, _) in enumerate(pic.getdata()):
        byte = (byte << 1) | (red & 1)
        if index % 8 == 7:
            if byte == 0:
                return result.decode('utf-8')
            result.append(byte)
            byte = 0
    raise ValueError('No NUL-terminated payload found')

def recover_fat(path):
    """Read BPB geometry independently; enumerate live/deleted root entries."""
    data = path.read_bytes()
    bps = struct.unpack_from('<H', data, 11)[0]
    spc = data[13]
    reserved = struct.unpack_from('<H', data, 14)[0]
    fats = data[16]
    root_count = struct.unpack_from('<H', data, 17)[0]
    fat_size = struct.unpack_from('<H', data, 22)[0]
    root_start = (reserved + fats * fat_size) * bps
    data_start = root_start + ((root_count * 32 + bps - 1)//bps)*bps
    files = {}
    for pos in range(root_start, root_start + root_count*32, 32):
        entry = data[pos:pos+32]
        if entry[0] == 0:
            break
        deleted = entry[0] == 0xe5
        name = ('_' if deleted else chr(entry[0])) + entry[1:8].decode().rstrip() + '.' + entry[8:11].decode().rstrip()
        cluster = struct.unpack_from('<H', entry, 26)[0]
        size = struct.unpack_from('<I', entry, 28)[0]
        chunks = bytearray()
        while len(chunks) < size:
            offset = data_start + (cluster-2)*bps*spc
            chunks.extend(data[offset:offset+bps*spc])
            cluster = cluster+1 if deleted else struct.unpack_from('<H', data, reserved*bps+cluster*2)[0]
        files[name] = bytes(chunks[:size]).decode('utf-8')
    return files

def timeline(files):
    sessions = list(csv.DictReader(io.StringIO(files['SESSION.LOG'])))
    audits = [json.loads(line) for line in files['AUDIT.JSL'].splitlines()]
    event = next(a for a in audits if a['case']=='MN06-0217' and a['action']=='preserve_pre_change_manifest')
    matched = [s for s in sessions if s['case']==event['case'] and s['session']==event['session']]
    start = next(s for s in matched if s['action']=='start')
    end = next(s for s in matched if s['action']=='end')
    release = next(r for r in csv.DictReader(io.StringIO(files['RELEASE.CSV'])) if r['record']==event['record'])
    return dict(service=start['service'], start=start['timestamp'], end=end['timestamp'], manifest_sha256=release['manifest_sha256'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['png','cipher','fat'])
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    if args.mode == 'png': print(extract_png(args.path))
    elif args.mode == 'cipher': print(transform(args.path.read_text(encoding='utf-8'), decrypt=True))
    else:
        files = recover_fat(args.path)
        print(json.dumps(files,indent=2))
        print(json.dumps(timeline(files),indent=2))
