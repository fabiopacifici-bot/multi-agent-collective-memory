---
name: collective-memory-curator
description: Memory hygiene and curation companion for multi-agent collective memory. Dedup, schema validation, cleanup routines, audit policies, dead-entry detection.
version: 1.0.0
user-invokable: true
commands:
  - /curator-validate
  - /curator-audit
  - /curator-sweep
  - /curator-dedup
  - /curator-reindex
  - /curator-missing
---

# Collective Memory Curator

Companion skill for `collective-memory`. The collective memory service has no auth, no dedup, no schema enforcement — this skill fills those gaps.

**Workspace location:** `~/.openclaw/workspace/skills/collective-memory-curator/`

---

## Why This Exists

The collective memory is a shared knowledge base for all NSA Agency agents (Olly, Marty, Molly, Lawy, Sage). Every agent can read and write. The service trusts all agents equally — which is fine when everyone follows the rules. But:

- **No auth** → any agent can write anything
- **No dedup** → same fact can be stored under multiple keys
- **No schema** → entries without required fields, malformed YAML, missing timestamps
- **No expiry** → stale entries accumulate indefinitely
- **No audit** → no one reviews what was written

This skill defines the **policies, validation routines, and curation procedures** that keep the collective memory trustworthy.

---

## Schema Validation (pre-write gate)

Every memory entry (local file or network API) MUST have:

```yaml
---
date: YYYY-MM-DD
agent: <agent-id>          # olly | marty | molly | lawy | sage
topic: <short-descriptor>  # single concept, lowercase-hyphenated
tags: [tag1, tag2]         # at least 1, max 5
confidence: confirmed      # confirmed | plausible | draft
---
```

### Validation Rules

| Field | Rule |
|-------|------|
| `date` | Must be ISO-8601 date (`YYYY-MM-DD`). No ISO datetimes. |
| `agent` | Must match a known agent id. Reject unknown agents. |
| `topic` | Lowercase, hyphenated, max 50 chars. Single concept only. |
| `tags` | Min 1, max 5. Each lowercase, hyphenated, max 30 chars. |
| `confidence` | One of: `confirmed`, `plausible`, `draft`. |
| Body | Min 1 sentence, max 500 words. Must contain a meaningful statement. |

### Validation Script

```bash
python3 {skill_dir}/scripts/validate.py <file-or-key>
python3 {skill_dir}/scripts/validate.py --all   # validate ALL entries
python3 {skill_dir}/scripts/validate.py --all --json | head -c 500
```

---

## Dedup Detection

Before writing a new entry, check if the same information already exists.

```bash
python3 {skill_dir}/scripts/dedup.py --query "negotiation status Boolean IP"
# Output: ⚠️ Potential duplicate (score: 0.92) — entries/2026-04-14-boolean-negotiation-status.md
```

Checks local entries via semantic search (embedding similarity > 0.85 threshold).

---

## Curation: Weekly Sweep

Recommended: every Sunday at 02:00 (or on demand via `/curator-sweep`)

```bash
python3 {skill_dir}/scripts/sweep.py           # dry run (report only)
python3 {skill_dir}/scripts/sweep.py --apply   # apply cleanup actions
```

The sweep:
1. **Stale detection** — entries older than 90 days with `confidence: draft` → flag
2. **Orphan entries** — entries not referenced in `index.md` → list
3. **Broken YAML** — entries with invalid frontmatter → flag
4. **Empty bodies** — entries with no body content → suggest delete
5. **Duplicate clusters** — group entries by semantic similarity >0.85 → flag

---

## Rebuild Index

The `index.md` only lists 11 entries — but there are 405 files in `entries/`. Fix that:

```bash
python3 {skill_dir}/scripts/reindex.py
```

Reads all `.md` files in `entries/`, extracts YAML frontmatter, rewrites `index.md` with complete month-grouped table.

---

## Quality Policy

| Confidence | Meaning | Retention |
|------------|---------|-----------|
| `confirmed` | Verified fact or decision | Permanent |
| `plausible` | Likely true, not yet verified | Max 30 days |
| `draft` | Brainstorming, incomplete | Max 7 days |

All agents should use `draft` when starting a line of reasoning and promote to `confirmed` or `plausible` after verification.

---

## Commands

| Command | Action |
|---------|--------|
| `/curator-validate <path>` | Validate a single entry against schema |
| `/curator-validate --all` | Full validation sweep of all entries |
| `/curator-dedup --query "..."` | Check for duplicates before writing |
| `/curator-sweep` | Run weekly sweep (dry-run) |
| `/curator-sweep --apply` | Run sweep with cleanup |
| `/curator-reindex` | Rebuild `index.md` from all entry files |
| `/curator-missing` | List entries not in `index.md` |

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/validate.py` | Schema validation (file or API key) |
| `scripts/dedup.py` | Semantic dedup check |
| `scripts/sweep.py` | Weekly curation sweep |
| `scripts/reindex.py` | Rebuild index.md from entries/ |
| `scripts/sign.py` | Add provenance stamp to an entry |
| `scripts/verify.py` | Verify provenance stamp |

---

## Routine Integration

Recommended cron: `curator-sweep` every Sunday at 02:00
Recommended pre-write hook: agents should run `/curator-dedup` before creating a new memory entry, and `/curator-validate` before committing the file.

---

## Best Practices

1. **Dedup before write** — always check with `/curator-dedup` before creating a new entry
2. **Start at draft** — use `draft` confidence initially, promote after verification
3. **One fact per entry** — each entry should express exactly one fact, decision, or insight
4. **Use consistent tags** — reuse existing tags rather than creating new ones
5. **Sign on creation** — run `/sign.py` immediately after writing
6. **Review old drafts weekly** — promote, update, or delete during the sweep