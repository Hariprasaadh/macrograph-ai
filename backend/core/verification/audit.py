"""Append-only local audit snapshots; caller retains report if storage fails."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import uuid


def _save(report: dict, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    audit_id = 'audit_' + uuid.uuid4().hex
    stored = {**report}
    if 'persistence' in stored:
        stored['persistence'] = {'status': 'saved', 'audit_id': audit_id}
    payload = json.dumps(stored, ensure_ascii=True, allow_nan=False)
    with sqlite3.connect(path, timeout=5) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS claim_audits (audit_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, report TEXT NOT NULL)')
        conn.execute('INSERT INTO claim_audits VALUES (?, ?, ?)',
                     (audit_id, datetime.now(timezone.utc).isoformat(), payload))
    return audit_id


async def save_audit(report: dict, path: Path) -> str:
    return await asyncio.to_thread(_save, report, path)


def load_audit(audit_id: str, path: Path) -> dict:
    with sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True) as conn:
        row = conn.execute('SELECT report FROM claim_audits WHERE audit_id = ?', (audit_id,)).fetchone()
    if row is None:
        raise KeyError(audit_id)
    return json.loads(row[0])
