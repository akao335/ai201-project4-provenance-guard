import json
import os
from datetime import datetime, timezone

LOG_FILE = "audit_log.json"

def _read_log():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def _write_log(entries):
    with open(LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)

def add_entry(entry: dict):
    entries = _read_log()
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    entries.append(entry)
    _write_log(entries)
    return entry

def get_log(limit: int = 20):
    entries = _read_log()
    return entries[-limit:]

def find_entry(content_id: str):
    entries = _read_log()
    for entry in reversed(entries):
        if entry.get("content_id") == content_id:
            return entry
    return None

def update_entry(content_id: str, updates: dict):
    entries = _read_log()
    for entry in entries:
        if entry.get("content_id") == content_id:
            entry.update(updates)
    _write_log(entries)