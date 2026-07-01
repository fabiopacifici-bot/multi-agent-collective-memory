---
name: collective-memory-client
description: Client for the multi-agent collective memory API (port 8010). Read, write, search shared memory across the LAN.
version: 1.0.0
user-invokable: true
commands:
  - /memory-read
  - /memory-write
  - /memory-search
  - /memory-recent
---

# Collective Memory Client

Client skill for the **Multi-Agent Collective Memory** service running on port 8010. Any agent on the LAN can read/write/search shared memories.

**API Service:** `http://<olly-host>:8010` (set `COLLECTIVE_MEMORY_API` env var to override)

---

## CLI Usage

```bash
# Create a memory
python3 {skill_dir}/scripts/memory_api.py create \
  --agent olly --key my-key --text "content here"

# Get by key
python3 {skill_dir}/scripts/memory_api.py get key my-key

# Semantic search
python3 {skill_dir}/scripts/memory_api.py search "query" --top 5

# Recent memories
python3 {skill_dir}/scripts/memory_api.py recent --limit 10 --agent olly

# Delete
python3 {skill_dir}/scripts/memory_api.py delete my-key

# Health check
python3 {skill_dir}/scripts/memory_api.py health
```

## Python Import

```python
from memory_api import create_memory, search_memory, get_memory_by_key, recent_memories, delete_memory, health

status = health()
result = create_memory("marty", "project-status", text="Phase 1 done")
results = search_memory("project status", top_k=3)
```

## Raw HTTP

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service status |
| `POST` | `/memory` | Create memory |
| `GET` | `/memory/{id}` | Get by ID |
| `GET` | `/memory/key/{key}` | Get by key |
| `GET` | `/memory/search?q=...&top_k=5` | Semantic search |
| `GET` | `/memory/recent?limit=10&agent=...` | Recent memories |
| `DELETE` | `/memory/{key}` | Delete by key |

```bash
curl http://localhost:8010/health
curl http://localhost:8010/memory/recent?limit=5
```

---

## Env Config

| Variable | Default | Description |
|----------|---------|-------------|
| `COLLECTIVE_MEMORY_API` | `http://localhost:8010` | API base URL |