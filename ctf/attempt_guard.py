"""Small persistent SQLite limiter shared by portal worker processes."""
import math
import sqlite3
import time
from pathlib import Path


def reserve(path, identity, limits=((60, 5), (3600, 30))):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    with sqlite3.connect(path, timeout=15) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS guard (identity TEXT, at REAL)')
        conn.execute('CREATE INDEX IF NOT EXISTS guard_identity_at ON guard(identity, at)')
        conn.execute('BEGIN IMMEDIATE')
        retry = 0
        for seconds, maximum in limits:
            rows = conn.execute('SELECT at FROM guard WHERE identity=? AND at>? ORDER BY at',
                                (identity, now-seconds)).fetchall()
            if len(rows) >= maximum:
                retry = max(retry, math.ceil(rows[-maximum][0] + seconds - now))
        if not retry:
            conn.execute('INSERT INTO guard VALUES (?,?)', (identity, now))
        conn.execute('DELETE FROM guard WHERE at<?', (now-3600,))
    return retry
