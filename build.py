"""Build all immutable artifacts in dependency order. No runtime state is reset."""
import argparse
import hashlib
import html
import json
import shutil
import tarfile
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw
from ctf.cipher import transform
from ctf.fat import make_image

ROOT = Path(__file__).resolve().parent
FLAGS = [
    'FLAG{st01_follow_the_missing_identity_7c2e91a4}',
    'FLAG{st02_the_glitch_carries_a_message_b6f034d8}',
    'FLAG{st03_an_agent_signed_the_approval_28a9cf71}',
    'FLAG{st04_the_oracle_warned_you_d17b630e}',
    'FLAG{st05_the_deleted_minutes_survive_4ea280c9}',
    'FLAG{st06_verify_the_exit_before_you_trust_93fd61b2}',
]
DAY = '2026-02-17'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode('utf-8'))

def json_file(path, value):
    write(path, json.dumps(value, indent=2) + '\n')

def page(title, body):
    from ctf.presentation import archive_page
    return archive_page(title, body)


def build(out, portal_url='http://127.0.0.1:8083'):
    out = Path(out)
    for folder in ('stage1', 'portal', 'linux', 'organizer', 'handouts', 'verifier'):
        (out / folder).mkdir(parents=True, exist_ok=True)
    linux = out / 'linux'
    routes = {
        'EXIT-04': 'route_id=EXIT-04\nrelease_id=R17\nbackup_set=northstar-vault-20260217\nstatus=verified-offline\n',
        'EXIT-09': 'route_id=EXIT-09\nrelease_id=R18\nbackup_set=northstar-mirror-20260217\nstatus=approved\napprover_label=Maya Nair\n',
        'EXIT-02': 'route_id=EXIT-02\nrelease_id=R16\nbackup_set=northstar-vault-20260216\nstatus=retired\n',
    }
    for name, content in routes.items():
        write(linux / 'routes' / f'{name}.route', content)
    for release, route in [('R17', 'EXIT-04'), ('R18', 'EXIT-09'), ('R16', 'EXIT-02')]:
        content = f'# release_id={release}\n# route_id={route}\n{digest(linux / "routes" / (route + ".route"))}  routes/{route}.route\n'
        write(linux / 'manifests' / f'{release}.sha256', content)
    trusted_hash = digest(linux / 'manifests/R17.sha256')
    write(linux / 'logs/release.log', f'{DAY}T01:50:00Z release=R16 route=EXIT-02 action=retire\n{DAY}T02:11:00Z release=R17 route=EXIT-04 action=register event=REL-017\n{DAY}T02:25:00Z release=R18 route=EXIT-09 action=advertise event=REL-018\n')
    write(linux / 'logs/maintenance.log', f'{DAY}T02:10:00Z event=EVT-010 service=backup-check action=read_pointer\n{DAY}T02:17:00Z event=EVT-017 service=mn-sync session=S-217 action=start\n{DAY}T02:24:00Z event=EVT-024 service=mn-sync session=S-217 action=redirect old=EXIT-04 new=EXIT-09 label="Maya Nair"\n{DAY}T02:34:00Z event=EVT-034 service=mn-sync session=S-217 action=end\n')
    write(linux / 'README.txt', '''THE LAST BACKUP — Linux evidence
Case MN06-0217. Work in /home/analyst/work; evidence in /srv/northstar is read-only.
Inspect your user/group access, permissions and CURRENT_EXIT. Compare preserved
logs against the time window recovered in Stage 5. The current pointer is a claim.
Authenticate a candidate manifest using the trusted SHA-256 from the forensic
evidence, then verify the route named in that manifest from /srv/northstar.
Submit release ID, route ID, service identity and redirection event ID to the
organizer-provided verification console. Do not use a real backup or restore data.
''')
    # Tar preserves a real symbolic link and POSIX modes even on Windows hosts.
    with tarfile.open(out / 'organizer/linux-evidence.tar', 'w') as archive:
        for p in sorted(linux.rglob('*')):
            if p.is_file():
                data = p.read_bytes()
                info = tarfile.TarInfo(p.relative_to(linux).as_posix())
                info.size, info.mode, info.mtime = len(data), 0o440, 1771296000
                info.uid, info.gid, info.uname, info.gname = 0, 2000, 'root', 'evidence'
                archive.addfile(info, BytesIO(data))
        link = tarfile.TarInfo('CURRENT_EXIT')
        link.type, link.linkname, link.mode = tarfile.SYMTYPE, 'routes/EXIT-09.route', 0o777
        archive.addfile(link)

    sessions = f'''timestamp,case,session,service,action
{DAY}T02:05:00Z,MN06-0199,S-199,mn-sync,start
{DAY}T02:08:00Z,MN06-0199,S-199,mn-sync,end
{DAY}T02:15:00Z,MN06-0217,S-218,backup-check,start
{DAY}T02:16:00Z,MN06-0217,S-218,backup-check,end
{DAY}T02:17:00Z,MN06-0217,S-217,mn-sync,start
{DAY}T02:34:00Z,MN06-0217,S-217,mn-sync,end
'''
    audit_rows = [
        dict(time=f'{DAY}T02:16:00Z', case='MN06-0217', session='S-218', event='A-216', action='read', record='REL-016'),
        dict(time=f'{DAY}T02:18:00Z', case='MN06-0217', session='S-217', event='A-218', action='preserve_pre_change_manifest', record='REL-017'),
        dict(time=f'{DAY}T02:25:00Z', case='MN06-0217', session='S-217', event='A-225', action='advertise_replacement', record='REL-018'),
    ]
    release_index = 'record,manifest_sha256,classification\n' + '\n'.join(
        f'REL-0{n},{digest(linux / "manifests" / ("R"+str(n)+".sha256"))},{label}'
        for n, label in [(16, 'retired'), (17, 'preserved'), (18, 'advertised')]) + '\n'
    handover = f'''PRIVATE HANDOVER — Case MN06-0217
{FLAGS[4]}
The maintenance export is missing part of the night. Join SESSION.LOG and
AUDIT.JSL by case and session; identify the service and its UTC start/end.
Find the audit event preserving the pre-change manifest. Join its record to
RELEASE.CSV for the trusted manifest SHA-256. Keep this hash for Stage 6.
Ask the organizer for an analyst SSH account and verifier token after scoring.
Elias
'''
    image_path = out / 'handouts/northstar_evidence.img'
    entries = make_image(image_path, {
        'README.TXT': 'Northstar preserved evidence. Case MN06-0217. All log timestamps are UTC. Analyse a copy. The visible export is incomplete.\n',
        'SESSION.LOG': sessions,
        'AUDIT.JSL': '\n'.join(json.dumps(row) for row in audit_rows) + '\n',
        'RELEASE.CSV': release_index,
        'EXPORT.LOG': f'{DAY}T02:16:00Z export heartbeat OK\n{DAY}T02:35:00Z export heartbeat OK\n',
    }, ('HANDOVER.TXT', handover))
    plaintext = f'''Maya was right. The approval label cannot establish authority.
{FLAGS[3]}
Preserve northstar_evidence.img before analysing a working copy.
SHA-256: {digest(image_path)}
Recover the deleted handover; corroborate its claims with preserved logs.
Elias
'''
    write(out / 'portal/elias.enc.txt', transform(plaintext))
    write(out / 'portal/training-memo.txt', '''NORTHSTAR LEGACY RECOVERY TRAINING
Project keyword: ORACLE
Our classroom repeating-key cipher uses A=0 through Z=25.
Encrypt: C=(P+K) mod 26. Decrypt: P=(C-K) mod 26.
Advance the key only on ASCII letters A-Z or a-z. Preserve case, punctuation,
digits, braces, underscores, spaces and newlines. Continue the key across
lines; restart at the beginning of a file. Read and write UTF-8.
Check example: ABC abc! encrypts to OSC cmg!
This is an educational historical cipher, not modern data protection.
After solving and scoring Stage 4, ask the organizer for the named image.
''')
    transactions = [
        dict(id='TX-211', reference='APR-0217', time='02:11:00', account='elias', role='backup-admin', label='Elias Rowan', action='approve'),
        dict(id='TX-217', reference='APR-0217', time='02:23:00', account='mn-sync', role='sync-agent', label='Maya Nair', action='approve'),
        dict(id='TX-218', reference='APR-0218', time='02:26:00', account='mn-sync', role='sync-agent', label='Maya Nair', action='read'),
    ]
    audit = [
        dict(id='AUD-211', transaction='TX-211', reference='APR-0217', account='elias', role='backup-admin', action='approve', result='accepted', date=DAY),
        dict(id='AUD-217', transaction='TX-217', reference='APR-0217', account='mn-sync', role='sync-agent', action='approve', result='accepted', date=DAY),
        dict(id='AUD-219', transaction='TX-217', reference='APR-0217', account='mn-sync', role='sync-agent', action='approve', result='denied', date=DAY),
        dict(id='AUD-218', transaction='TX-218', reference='APR-0218', account='mn-sync', role='sync-agent', action='read', result='accepted', date=DAY),
    ]
    json_file(out / 'portal/fixtures.json', dict(policy=[dict(role=r, can_approve=a) for r,a in [('employee',False),('sync-agent',False),('backup-admin',True)]], transactions=transactions, audit=audit))
    json_file(out / 'portal/private.json', dict(flag=FLAGS[2], evidence_pair=['TX-217','AUD-217']))
    json_file(out / 'verifier/answer.json', dict(flag=FLAGS[5], answer=dict(release_id='R17', route_id='EXIT-04', service='mn-sync', event_id='EVT-024')))

    # Code-drawn original event image; its pixels are the challenge data carrier.
    pic = Image.new('RGB', (960, 540), '#162d39')
    draw = ImageDraw.Draw(pic)
    for y in range(540):
        draw.line((0,y,960,y), fill=(18+y//18, 35+y//12, 48+y//10))
    draw.ellipse((710,55,810,155), fill='#f1cc83')
    for i in range(10):
        x, top = 45+i*92, 210+(i%3)*25
        draw.rectangle((x,top,x+64,445), fill='#0e2630')
        for row in range(6):
            draw.rectangle((x+13,top+15+row*29,x+50,top+24+row*29), fill='#659f9b')
    draw.rectangle((0,445,960,540), fill='#10222b')
    draw.text((40,465), 'NORTHSTAR LABS  |  RECOVERY READINESS  |  2026-02-17 01:40 UTC', fill='#dbe9e4')
    note = f'{FLAGS[1]}\nCase MN06-0217. Approval reference APR-0217.\nEvidence portal: {portal_url}\nMaya\n'.encode() + b'\x00'
    pixels = pic.load()
    for i in range(len(note)*8):
        x,y = i % pic.width, i // pic.width
        r,g,b = pixels[x,y]
        pixels[x,y] = ((r & 254) | ((note[i//8] >> (7-i%8)) & 1), g, b)
    pic.save(out / 'stage1/event-original.png', optimize=False)
    write(out / 'stage1/pixel-note.txt', 'Use the original lossless PNG. Read one least-significant bit from each red channel, left to right, top to bottom. Assemble bytes most-significant bit first, decode UTF-8, stop at NUL (00).\n')
    shutil.copyfile(ROOT / 'ctf/static/style.css', out / 'stage1/style.css')
    write(out / 'stage1/index.html', page('The Missing Employee', '''<p class="eyebrow">01 / OSINT</p><h1>The missing employee.</h1><p class="lead">Maya noticed something wrong with the recovery route. Then her account disappeared. The archive still remembers.</p><div class="cards"><section><h2>Staff directory</h2><p>The current record, last revised after the incident.</p><a href="/staff.html">Read staff records →</a></section><section><h2>Event register</h2><p>A preserved calendar record from the original meeting.</p><a href="/events.html">Check the register →</a></section><section><h2>Announcement archive</h2><p>Three notices. Compare the case reference and event time.</p><a href="/archive.html">Explore the archive →</a></section></div>'''))
    write(out / 'stage1/staff.html', page('Staff directory', '<p class="eyebrow">CURRENT DIRECTORY · REVISED 2026-02-18</p><h1>People at Northstar.</h1><section><h2>Maya Nair</h2><p>Employee ID MN06 · Records assistant · Recovery case MN06-0199</p><p>Current status: account disabled. No recovery approvals recorded in this directory.</p><a href="/events.html">Preserved event register →</a></section>'))
    write(out / 'stage1/events.html', page('Event register', '<p class="eyebrow">PRESERVED BEFORE DIRECTORY REVISION</p><h1>Recovery readiness meeting.</h1><section><p>Attendee: Maya Nair · Employee MN06</p><p>Case reference: <strong>MN06-0217</strong></p><p>Event time: <strong>2026-02-17 01:40 UTC</strong></p><p>Recorder: Elias Rowan</p><a href="/archive.html">Compare archived notices →</a></section>'))
    write(out / 'stage1/archive.html', page('Archive', '<p class="eyebrow">ANNOUNCEMENTS</p><h1>From the archive.</h1><section><p><a href="/notice-061.html">17 February · Recovery readiness briefing</a></p><p><a href="/notice-062.html">17 February · Team meeting record</a></p><p><a href="/notice-063.html">17 February · Recovery review note</a></p></section>'))
    for n,case,time in [(61,'MN06-0199','01:40'),(62,'MN06-0217','01:40'),(63,'MN06-0217','01:50')]:
        extra = f'<p class="flag">{FLAGS[0]}</p><p><a href="/event-original.png" download>Download original event image ↓</a> · <a href="/pixel-note.txt">Image handling note</a></p>' if n == 62 else '<p>No corroborating handover is attached to this notice.</p>'
        write(out / f'stage1/notice-0{n}.html', page('Archived notice', f'<p class="eyebrow">PUBLISHED 2026-02-17 · NOTICE 0{n}</p><h1>Recovery readiness.</h1><section><p>Maya Nair attended the briefing for case <strong>{case}</strong>.</p><p>Meeting timestamp: <strong>{DAY} {time} UTC</strong>.</p>{extra}</section>'))

    titles = ['The Missing Employee','More Than a Photograph','Someone Used Her Name','The Administrator’s Warning','Seventeen Missing Minutes','The Wrong Recovery Route']
    domains = ['OSINT','Steganography','Web Security','Cryptography','Digital Forensics','Linux Security']
    descriptions = [
        'Compare the staff directory, preserved event register and archived notices. Match both case and timestamp. Open the Stage 1 archive at {archive_url}.',
        'Recover Maya’s note from the original PNG obtained in Stage 1. Read red-channel least-significant bits, row-major, MSB-first bytes, UTF-8 to NUL. Preserve the original.',
        'Use APR-0217 to compare policy, transaction and audit records at {portal_url}. Submit the corroborating pair to release the encrypted warning.',
        'Decrypt Elias’s message using the supplied training memo. Submit the recovered flag, then request northstar_evidence.img from your organizer. Check its SHA-256 before analysis.',
        'Recover the deleted handover from the 64 MiB FAT16 raw image (filesystem offset zero). Correlate SESSION.LOG, AUDIT.JSL and RELEASE.CSV. Retain the service, UTC window and trusted manifest hash. Ask the organizer for Stage 6 access after scoring.',
        'Use your issued analyst SSH account to investigate /srv/northstar. Authenticate the manifest and then its route. Submit release, route, service and redirection event at {verifier_url}, then submit the returned flag here.',
    ]
    hints = [
        [('Check announcements older than the directory.',5),('Match both case reference and UTC meeting time.',10)],
        [('Use the original image pixels.',5),('Read only red-channel least-significant bits.',10)],
        [('Authentication and approval permission are different.',10),('Match the accepted audit event to the policy and transaction.',20)],
        [('The key repeats: ORACLE.',10),('A=0; only ASCII letters advance the key, including across lines.',20)],
        [('Analyse a copy and enumerate deleted entries.',15),('Recover the handover, then join case, session and release record IDs.',30)],
        [('Inspect the pointer and its history.',20),('Authenticate the manifest first, then check its route hash.',40)],
    ]
    challenges = [dict(stage=str(i+1), name=f'{i+1:02d} · {title}', category=domains[i], value=[100,100,200,200,250,300][i], description=descriptions[i], flag=FLAGS[i], hints=[dict(content=t,cost=c) for t,c in hints[i]]) for i,title in enumerate(titles)]
    json_file(out / 'organizer/challenges.json', challenges)
    split = json.loads(json.dumps(challenges))
    split[4].update(stage='5A', name='05A · Recover the Deleted Handover', value=100, hints=[dict(content=t,cost=c) for t,c in [('The visible file list is incomplete.',5),('Enumerate deleted entries and recover the handover.',10)]])
    split.insert(5, dict(stage='5B', name='05B · Reconstruct the Missing Minutes', category='Digital Forensics', value=150, description='Join case and session records and identify the UTC window. Construct FLAG{st05b_<service>_<startHHMM>_<endHHMM>} using the literal lowercase service and four-digit times. Retain the trusted manifest hash.', flag='FLAG{st05b_mn-sync_0217_0234}', hints=[dict(content='Compare preserved sessions with the export.',cost=10),dict(content='Join by case and session; use UTC start and end.',cost=20)]))
    json_file(out / 'organizer/challenges-split5.json', split)
    write(out / 'organizer/stage4-plaintext.txt', plaintext)
    write(out / 'organizer/recovered-handover.txt', handover)
    json_file(out / 'organizer/fat-entries.json', entries)
    register = dict(release='last-backup-1.0', date=DAY, case='MN06-0217', trusted_manifest_sha256=trusted_hash, files={})
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name != 'release-register.json':
            register['files'][p.relative_to(out).as_posix()] = dict(bytes=p.stat().st_size, sha256=digest(p))
    json_file(out / 'organizer/release-register.json', register)
    print(f'Built {len(register["files"])} artifacts. Image SHA-256: {digest(image_path)}')
    return register

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'build')
    parser.add_argument('--portal-url', default='http://127.0.0.1:8083')
    args = parser.parse_args()
    build(args.output, args.portal_url)
