#!/usr/bin/env python3
"""
search.py — Semantic search over collective memory entries.

Usage:
  python3 search.py "what happened with Boolean?"
  python3 search.py "IP licensing terms" --top 5
  python3 search.py "recent course updates" --json
"""
import os
import sys
import json
import sqlite3
import math
import requests
from pathlib import Path

BASE_DIR  = Path(__file__).parent.parent
DB_PATH   = BASE_DIR / "memory.db"
EMBED_URL = os.environ.get("COLLECTIVE_EMBED_URL", "http://localhost:8770/embeddings")
DEFAULT_TOP_K = 3


def cosine(a: list, b: list) -> float:
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def embed(text: str) -> list[float] | None:
    # Try HTTP embedding server first
    try:
        r = requests.post(EMBED_URL, json={"input": text}, timeout=5)
        d = r.json()
        vec = d.get("data", [None])[0]
        if vec:
            return vec
    except Exception:
        pass
    # Fallback: native SentenceTransformer in-process
    try:
        import sys, os as _os
        _model_path = _os.environ.get(
            "COLLECTIVE_EMBED_MODEL",
            "/mnt/e/models/huggingface/hub_cache/models--unsloth--embeddinggemma-300m-qat-q8_0-unquantized/snapshots/dc4294deb8cbaad174042a020037fb3a5b008976"
        )
        from sentence_transformers import SentenceTransformer
        _st = SentenceTransformer(_model_path)
        return _st.encode(text).tolist()
    except Exception as e:
        print(f"[search] Embed fallback error: {e}", file=sys.stderr)
        return None


def search(query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    if not DB_PATH.exists():
        return []

    q_vec = embed(query)
    if q_vec is None:
        return []

    db = sqlite3.connect(str(DB_PATH))
    rows = db.execute(
        "SELECT id, filename, date, agent, topic, tags, title, body, embedding FROM entries"
    ).fetchall()
    db.close()

    scored = []
    for row in rows:
        e_vec = json.loads(row[8])
        score = cosine(q_vec, e_vec)
        scored.append({
            "score": round(score, 4),
            "id": row[0],
            "filename": row[1],
            "date": row[2],
            "agent": row[3],
            "topic": row[4],
            "tags": row[5],
            "title": row[6],
            "body": row[7][:300] + ("..." if len(row[7]) > 300 else ""),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def format_results(results: list[dict]) -> str:
    if not results:
        return "No relevant memories found."
    lines = [f"🧠 Collective Memory — top {len(results)} results:\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"**{i}. {r['title']}** (score: {r['score']})")
        lines.append(f"   📅 {r['date']} · 🤖 {r['agent']} · 🏷 {r['topic']}")
        lines.append(f"   {r['body']}\n")
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Usage: python3 search.py <query> [--top N] [--json]")
        sys.exit(1)

    query  = " ".join(args)
    top_k  = int(next((sys.argv[sys.argv.index("--top") + 1] for i, a in enumerate(sys.argv) if a == "--top"), DEFAULT_TOP_K))
    as_json = "--json" in sys.argv

    results = search(query, top_k)

    if as_json:
        print(json.dumps(results, indent=2))
    else:
        print(format_results(results))
