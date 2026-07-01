#!/usr/bin/env python3
"""
index.py — Index collective memory entries into SQLite with embeddings.

Usage:
  python3 index.py              # index all entries (skip already indexed)
  python3 index.py --rebuild    # wipe and rebuild from scratch
  python3 index.py --watch      # index then watch for new files
"""
import os
import re
import sys
import json
import sqlite3
import hashlib
import time
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent.parent
ENTRIES_DIR = BASE_DIR / "entries"
DB_PATH     = BASE_DIR / "memory.db"
EMBED_URL   = os.environ.get("COLLECTIVE_EMBED_URL", "http://localhost:8770/embeddings")


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            filename TEXT,
            date TEXT,
            agent TEXT,
            topic TEXT,
            tags TEXT,
            confidence TEXT,
            title TEXT,
            body TEXT,
            embedding BLOB,
            indexed_at TEXT
        )
    """)
    db.commit()
    return db


def parse_entry(path: Path) -> dict | None:
    text = path.read_text()
    # Extract YAML frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not fm_match:
        return None
    fm_text, body = fm_match.group(1), fm_match.group(2).strip()
    fm = {}
    for line in fm_text.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            fm[k.strip()] = v.strip().strip("[]").replace("'", "").replace('"', '')
    # Extract title from first # heading
    title_match = re.search(r"^# (.+)", body, re.MULTILINE)
    title = title_match.group(1) if title_match else path.stem
    # Clean body (remove heading)
    clean_body = re.sub(r"^# .+\n+", "", body).strip()
    return {
        "id": hashlib.sha256(path.name.encode()).hexdigest()[:16],
        "filename": path.name,
        "date": fm.get("date", ""),
        "agent": fm.get("agent", "unknown"),
        "topic": fm.get("topic", ""),
        "tags": fm.get("tags", ""),
        "confidence": fm.get("confidence", "confirmed"),
        "title": title,
        "body": clean_body,
    }


def embed(text: str) -> list[float] | None:
    try:
        r = requests.post(EMBED_URL, json={"input": text}, timeout=10)
        d = r.json()
        return d.get("data", [None])[0]
    except Exception as e:
        print(f"  [embed] Error: {e}")
        return None


def index_entry(db, entry: dict) -> bool:
    # Build text to embed: title + topic + tags + body
    embed_text = f"{entry['title']}\n{entry['topic']} {entry['tags']}\n{entry['body']}"
    vec = embed(embed_text)
    if vec is None:
        return False
    db.execute("""
        INSERT OR REPLACE INTO entries
        (id, filename, date, agent, topic, tags, confidence, title, body, embedding, indexed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry["id"], entry["filename"], entry["date"], entry["agent"],
        entry["topic"], entry["tags"], entry["confidence"], entry["title"],
        entry["body"], json.dumps(vec), datetime.now().isoformat()
    ))
    db.commit()
    return True


def run(rebuild=False, watch=False):
    db = get_db()
    if rebuild:
        db.execute("DELETE FROM entries")
        db.commit()
        print("[index] Rebuilding from scratch...")
    else:
        print("[index] Indexing new/updated entries...")

    indexed, skipped = 0, 0
    existing_ids = {row[0] for row in db.execute("SELECT id FROM entries")}

    for path in sorted(ENTRIES_DIR.glob("*.md")):
        entry = parse_entry(path)
        if not entry:
            continue
        if not rebuild and entry["id"] in existing_ids:
            skipped += 1
            continue
        print(f"  + {path.name} [{entry['topic']}]")
        if index_entry(db, entry):
            indexed += 1
        else:
            print(f"    ⚠ embedding failed, skipped")

    print(f"[index] Done — {indexed} indexed, {skipped} skipped. DB: {DB_PATH}")

    if watch:
        print("[index] Watching for new entries (Ctrl+C to stop)...")
        known = {p.name for p in ENTRIES_DIR.glob("*.md")}
        while True:
            time.sleep(10)
            current = {p.name for p in ENTRIES_DIR.glob("*.md")}
            new_files = current - known
            for name in new_files:
                path = ENTRIES_DIR / name
                entry = parse_entry(path)
                if entry:
                    print(f"  + new: {name}")
                    index_entry(db, entry)
            known = current


if __name__ == "__main__":
    rebuild = "--rebuild" in sys.argv
    watch   = "--watch" in sys.argv
    run(rebuild=rebuild, watch=watch)
