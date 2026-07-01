#!/usr/bin/env python3
"""
memory_api.py — Client wrapper for the Multi-Agent Collective Memory REST API.

Allows agents to read/write/search shared memory over the network.
Supports both CLI and Python import usage.

CLI Usage:
  python3 memory_api.py create --agent olly --key my-key --text "Hello world"
  python3 memory_api.py get id 1
  python3 memory_api.py get key my-key
  python3 memory_api.py search "query text" --top 5
  python3 memory_api.py recent --limit 10 --agent olly
  python3 memory_api.py delete my-key

Python import:
  from memory_api import create_memory, search_memory, get_memory_by_key
"""
import sys
import json
import os
import argparse
from typing import Any

import requests

API_BASE = os.environ.get("COLLECTIVE_MEMORY_API", "http://localhost:8010")


def _url(path: str) -> str:
    return f"{API_BASE}{path}"


def health() -> dict:
    """Check if the collective memory service is running."""
    try:
        r = requests.get(_url("/health"), timeout=3)
        return r.json()
    except requests.ConnectionError:
        return {"status": "unreachable", "error": f"Cannot connect to {API_BASE}"}


def create_memory(agent: str, key: str, text: str = "", images: list[str] | None = None,
                  metadata: dict | None = None) -> dict:
    """Create a new memory entry."""
    payload = {
        "agent": agent,
        "key": key,
        "content": {"text": text, "images": images or []},
        "metadata": metadata or {},
    }
    r = requests.post(_url("/memory"), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def get_memory_by_id(memory_id: int) -> dict:
    """Retrieve a memory by its primary key ID."""
    r = requests.get(_url(f"/memory/{memory_id}"), timeout=5)
    if r.status_code == 404:
        return {"error": "not_found"}
    r.raise_for_status()
    return r.json()


def get_memory_by_key(key: str) -> dict:
    """Retrieve a memory by its logical key."""
    r = requests.get(_url(f"/memory/key/{key}"), timeout=5)
    if r.status_code == 404:
        return {"error": "not_found"}
    r.raise_for_status()
    return r.json()


def update_memory(key: str, text: str = "", images: list[str] | None = None,
                  metadata: dict | None = None) -> dict:
    """Update an existing memory by key."""
    payload = {
        "content": {"text": text, "images": images or []},
    }
    if metadata is not None:
        payload["metadata"] = metadata
    r = requests.put(_url(f"/memory/{key}"), json=payload, timeout=10)
    if r.status_code == 404:
        return {"error": "not_found"}
    r.raise_for_status()
    return r.json()


def delete_memory(key: str) -> dict:
    """Delete a memory by its logical key."""
    r = requests.delete(_url(f"/memory/{key}"), timeout=5)
    if r.status_code == 404:
        return {"error": "not_found"}
    r.raise_for_status()
    return r.json()


def search_memory(query: str, top_k: int = 5) -> list[dict]:
    """Semantic search across all shared memories."""
    r = requests.get(_url(f"/memory/search"), params={"q": query, "top_k": top_k}, timeout=10)
    r.raise_for_status()
    return r.json()


def recent_memories(limit: int = 10, agent: str | None = None) -> list[dict]:
    """Get the most recent memories, optionally filtered by agent."""
    params = {"limit": limit}
    if agent:
        params["agent"] = agent
    r = requests.get(_url("/memory/recent"), params=params, timeout=5)
    r.raise_for_status()
    return r.json()


def embed_debug(text: str = "", images: list[str] | None = None) -> dict:
    """Debug endpoint: generate embedding without storing."""
    payload = {"text": text, "images": images or []}
    r = requests.post(_url("/embed"), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def format_results(results: list[dict], prefix: str = "🧠 Shared Memory") -> str:
    """Format search/recent results for display."""
    if not results:
        return f"{prefix} — no results."
    lines = [f"{prefix} — top {len(results)}:\n"]
    for r in results:
        score = f" (score: {r.get('score', ''):.4f})" if r.get("score") else ""
        lines.append(f"**{r.get('key', '?')}**{score}")
        lines.append(f"   🤖 {r.get('agent', '?')} · 📅 {r.get('created_at', '?')[:10]}")
        body = r.get("content_text", "")[:200]
        if body:
            lines.append(f"   {body}")
        lines.append("")
    return "\n".join(lines)


# ── CLI Entry Point ──

def cli():
    parser = argparse.ArgumentParser(description="Multi-Agent Collective Memory API client")
    sub = parser.add_subparsers(dest="command")

    # health
    sub.add_parser("health", help="Check service health")

    # create
    p_create = sub.add_parser("create", help="Create a memory")
    p_create.add_argument("--agent", required=True)
    p_create.add_argument("--key", required=True)
    p_create.add_argument("--text", default="")

    # get
    p_get = sub.add_parser("get", help="Get a memory by id or key")
    p_get.add_argument("mode", choices=["id", "key"])
    p_get.add_argument("value")

    # update
    p_update = sub.add_parser("update", help="Update a memory by key")
    p_update.add_argument("--key", required=True)
    p_update.add_argument("--text", default="")

    # delete
    p_del = sub.add_parser("delete", help="Delete a memory by key")
    p_del.add_argument("key")

    # search
    p_search = sub.add_parser("search", help="Semantic search")
    p_search.add_argument("query")
    p_search.add_argument("--top", type=int, default=5)

    # recent
    p_recent = sub.add_parser("recent", help="List recent memories")
    p_recent.add_argument("--limit", type=int, default=10)
    p_recent.add_argument("--agent", default=None)

    args = parser.parse_args()

    if args.command == "health":
        print(json.dumps(health(), indent=2))
    elif args.command == "create":
        r = create_memory(args.agent, args.key, text=args.text)
        print(json.dumps(r, indent=2))
    elif args.command == "get":
        r = get_memory_by_id(int(args.value)) if args.mode == "id" else get_memory_by_key(args.value)
        print(json.dumps(r, indent=2))
    elif args.command == "update":
        r = update_memory(args.key, text=args.text)
        print(json.dumps(r, indent=2))
    elif args.command == "delete":
        r = delete_memory(args.key)
        print(json.dumps(r, indent=2))
    elif args.command == "search":
        r = search_memory(args.query, top_k=args.top)
        print(format_results(r))
    elif args.command == "recent":
        r = recent_memories(limit=args.limit, agent=args.agent)
        print(format_results(r))
    else:
        parser.print_help()


if __name__ == "__main__":
    cli()