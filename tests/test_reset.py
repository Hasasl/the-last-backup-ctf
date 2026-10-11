"""Offline tests for the reset mechanism (no Docker needed)."""
import hashlib
import json
import os
import py_compile
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from ctf.verifier import create_app as verifier_app

ROOT = Path(__file__).resolve().parents[1]
RESET_VERIFIER = ROOT / 'local/reset_verifier.py'


def make_db(tmp_path):
    answer = tmp_path / 'answer.json'
    answer.write_text(json.dumps({'answer': dict(release_id='a', route_id='b', service='c', event_id='d'), 'flag': 'F'}))
    db_path = tmp_path / 'verifier.sqlite'
    verifier_app(dict(SECRET_KEY='x', ANSWER_FILE=answer, DATABASE=db_path))
    db = sqlite3.connect(db_path)
    for team in ('demo', 'team-01'):
        db.execute('INSERT INTO teams(id,token_hash) VALUES (?,?)', (team, hashlib.sha256(team.encode()).hexdigest()))
        db.execute('INSERT INTO completions VALUES (?,?)', (team, time.time()))
        for _ in range(3):
            db.execute('INSERT INTO attempts VALUES (?,?)', (team, time.time()))
    db.execute("INSERT INTO logins VALUES ('203.0.113.9',?)", (time.time(),))
    db.commit()
    db.close()
    return db_path


def run_reset(db_path, **env):
    full_env = dict(os.environ, RESET_DB=str(db_path), **env)
    done = subprocess.run([sys.executable, '-'], input=RESET_VERIFIER.read_text(), text=True,
                          capture_output=True, env=full_env, check=True)
    line = [l for l in done.stdout.splitlines() if l.startswith('RESET_JSON:')][-1]
    return json.loads(line[len('RESET_JSON:'):])


def counts(db_path):
    db = sqlite3.connect(db_path)
    try:
        return {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('teams', 'completions', 'attempts', 'logins')}
    finally:
        db.close()


def test_verifier_reset_one_team_keeps_others_and_all_tokens(tmp_path):
    db_path = make_db(tmp_path)
    result = run_reset(db_path, RESET_TEAM='team-01')
    assert result['remaining'] == {'attempts': 0, 'completions': 0}
    assert counts(db_path) == {'teams': 2, 'completions': 1, 'attempts': 3, 'logins': 0}
    db = sqlite3.connect(db_path)
    assert db.execute("SELECT COUNT(*) FROM completions WHERE team='demo'").fetchone()[0] == 1
    assert db.execute('SELECT COUNT(*) FROM teams WHERE enabled=1').fetchone()[0] == 2


def test_verifier_reset_all_keeps_teams_and_tokens(tmp_path):
    db_path = make_db(tmp_path)
    run_reset(db_path)
    assert counts(db_path) == {'teams': 2, 'completions': 0, 'attempts': 0, 'logins': 0}


def test_verifier_reset_dry_run_changes_nothing(tmp_path):
    db_path = make_db(tmp_path)
    before = counts(db_path)
    result = run_reset(db_path, RESET_DRY='1')
    assert result['dry_run'] is True and result['cleared']['completions'] == 2
    assert counts(db_path) == before


def test_verifier_reset_is_repeatable(tmp_path):
    db_path = make_db(tmp_path)
    run_reset(db_path)
    again = run_reset(db_path)
    assert again['cleared'] == {'attempts': 0, 'completions': 0, 'logins': 0}


def test_ctfd_reset_script_compiles_and_never_touches_challenges():
    py_compile.compile(str(ROOT / 'local/reset_ctfd.py'), doraise=True)
    source = (ROOT / 'local/reset_ctfd.py').read_text()
    deleted = re.findall(r"DELETE FROM ' \+ t|DELETE FROM (\w+)", source)
    for protected in ('challenges', 'flags', 'hints', 'pages', 'config'):
        assert protected not in [d for d in deleted if d]
    assert "PROGRESS = ['solves', 'fails', 'submissions', 'awards', 'unlocks', 'tracking']" in source
    assert "type='user'" in source and "type='admin'" not in source.split('DELETE FROM users')[-1][:40]


def test_reset_files_are_ascii_so_windows_powershell_reads_them():
    for name in ('reset.ps1', 'common.ps1', 'start.ps1', 'reset_ctfd.py', 'reset_verifier.py'):
        (ROOT / 'local' / name).read_bytes().decode('ascii')
    (ROOT / 'Reset Box.cmd').read_bytes().decode('ascii')


def test_reset_ps1_exposes_documented_switches():
    text = (ROOT / 'local/reset.ps1').read_text()
    for switch in ('Linux', 'Portal', 'Verifier', 'Team', 'Scores', 'Players', 'All', 'FullWipe',
                   'Backup', 'Status', 'DryRun', 'Yes', 'NoBackup'):
        assert re.search(r'\$' + switch + r'\b', text), switch
    assert text.count('{') == text.count('}') and text.count('(') == text.count(')')


def test_every_documented_switch_appears_in_readme():
    readme = (ROOT / 'README-LOCAL.md').read_text()
    assert 'Reset Box.cmd' in readme
    for switch in ('-Linux', '-Portal', '-Verifier', '-Scores', '-Players', '-All', '-FullWipe', '-DryRun'):
        assert switch in readme, switch



def test_no_machine_specific_paths_remain():
    paths = (
        list((ROOT / 'local').glob('*.ps1'))
        + list((ROOT / 'local').glob('*.py'))
        + [
            ROOT / 'README-LOCAL.md',
            ROOT / 'FULL-TEST-REPORT.md',
            ROOT / 'docs/RESET.md',
        ]
    )
    for path in paths:
        assert 'oshad' not in path.read_text(errors='ignore'), path



def test_verifier_init_builds_its_image_instead_of_pulling_it():
    """Regression: a fresh PC has no last-backup-full-verifier image, so the helper must build it."""
    text = (ROOT / 'compose.local.yml').read_text()
    block = re.split(r'(?m)^  verifier-init:', text)[1].split('\nvolumes:')[0]
    assert 'image: last-backup-full-verifier' in block and 'build: .' in block
