# Brief

A tiny web service with REST API to store and retrieve shared information among agents in a multi-agent system. The service will be designed to be lightweight and efficient, allowing agents to quickly access and update shared data as needed.

## Objective

Multimodal RAG shared memory over the network, with memory management and retrieval capabilities, to enable collaboration and coordination among agents in a multi-agent system.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLite
- Qwen3-VL-Embedding-2B (multimodal embedding model)
- Docker

## Embedding Model: Qwen3-VL-Embedding-2B

- **Model**: [Qwen/Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B)
- **Type**: Multimodal (text + images + video)
- **Parameters**: 2B
- **Embedding dimensions**: 1024 (configurable 64–2048)
- **Context length**: 32K tokenss
- **Hardware target**: GPU (CUDA) — inference ~50ms on RTX 3060
- **Fallback**: CPU (slower, ~500ms)
- **Dependencies**: `transformers>=4.57.0`, `qwen-vl-utils>=0.0.14`, `torch>=2.0.0`, `numpy`, `Pillow`, `pydantic`

### Supported Inputs

- **Text**: sent as JSON string
- **Images**: encoded as **Base64** inline in the JSON body (no file upload)
- **Multi-modal**: a single request can contain text + images — the model produces a single joint embedding

## Database Architecture (SQLite)

### `memories` table

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK, auto-increment |
| agent | TEXT | NOT NULL, indexed for lookup |
| key | TEXT | UNIQUE, logical key for the record |
| content_text | TEXT | Text content of the memory |
| content_images | TEXT | JSON array of Base64 images (optional) |
| embedding | BLOB | Vector of 1024 float32 (~4KB) |
| metadata | TEXT | JSON with arbitrary metadata |
| created_at | TIMESTAMP | Auto-set |
| updated_at | TIMESTAMP | Updated on PUT |

### Semantic Index

- Similarity via **cosine similarity** computed in-memory
- Embeddings deserialized from BLOB to `numpy.ndarray`
- For large datasets (>10K records): possible FAISS integration later

## API REST

### Endpoint definitivi

| Metodo | Path | Descrizione |
|--------|------|-------------|
| POST | `/memory` | Crea una nuova memoria. Body: `{ "agent": "millie", "key": "...", "content": { "text": "...", "images": ["base64..."] }, "metadata": {} }` |
| PUT | `/memory/{key}` | Aggiorna memoria esistente per chiave logica (rigenera embedding) |
| GET | `/memory/{id}` | Recupera una memoria per ID (PK) |
| GET | `/memory/search` | Ricerca semantica — embedding della query, top-K per cosine similarity. Param: `?q=...&top_k=5` |
| GET | `/memory/key/{key}` | Recupera una memoria per chiave esatta |
| GET | `/memory/recent` | Ultime N memorie. Param: `?limit=10&agent=millie` (filtro opzionale per agente) |
| DELETE | `/memory/{key}` | Delete memory by logical key |
| POST | `/embed` | Debug — embed without storage. Body: `{ "text": "...", "images": ["base64..."] }` → `{ "embedding": [...], "dim": 1024 }` |
| GET | `/health` | Health check — verify model loaded |

### Concurrency

- **Writes** (`POST`, `PUT`, `DELETE`): protected by `asyncio.Lock` — one at a time
- **Reads** (`GET`): fully concurrent (no lock)
- **Embedding**: unico modello caricato in memoria all'avvio (`lifespan` event di FastAPI)

## Network Exposure

- Server binds to `0.0.0.0:8010`
- Container Docker EXPOSE 8010
- Agents on the same Docker network (or host) can call `http://<host>:8010/memory/...`

### Docker & GPU CUDA

```dockerfile
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04
# CPU-only alternative: python:3.11-slim
```

To run with GPU:

```bash
docker run --gpus all -p 8010:8010 ...
```

If no GPU is available, the model falls back to CPU automatically.

## Components

1. REST API for shared memory management
2. Multimodal model Qwen3-VL-Embedding-2B for embeddings
3. Semantic search via cosine similarity
4. SQLite for persistence (concurrent reads, serial writes)
5. Docker for containerization and network exposure

## Constraints

- No authentication
- Sharable over the network (bind 0.0.0.0)
- Lightweight and efficient
- GPU optional (CPU fallback)
- Images as Base64 inline (no file storage)

## Expected Output

- Documented REST API (Swagger/OpenAPI via FastAPI)
- Multimodal semantic search (text + images)
- Full CRUD on shared memory
- Unit and integration tests
- Dockerfile for containerization

---

## Progress

| # | Feature | Branch | Status | Commit |
|---|---------|--------|--------|--------|
| 1 | Scheletro progetto + dipendenze + DB init | `feature/1-skeleton` | ✅ | `142f1ad` |
| 2 | `GET /health` + servizio embedding | `feature/2-health-embed` | ✅ | `f1f77de` |
| 3 | `POST /memory` | `feature/3-post-memory` | ✅ | `5de80df` |
| 4 | `GET /memory/{id}` + `GET /memory/key/{key}` | `feature/4-get-memory` | ✅ | `c66d9cc` |
| 5 | `PUT /memory/{key}` | `feature/5-put-memory` | ✅ | `0cd0662` |
| 6 | `GET /memory/search` | `feature/6-search` | ✅ | `ab61cda` |
| 7 | `GET /memory/recent` | `feature/7-recent` | ✅ | `d2faaa2` |
| 8 | `DELETE /memory/{key}` | `feature/8-delete` | ✅ | `82e9174` |
| 9 | `POST /embed` | `feature/9-embed` | ✅ | `50e14bd` |
| 10 | Dockerfile | `feature/10-docker` | ✅ | `7fad4d7` |
| 11 | Curator + Client skills (shipped with service) | `feat/curator-scripts` | ✅ | `c040599` |

## Shipped Skills

The repo ships two self-contained skills under `skills/`:

### collective-memory-client

Client skill for any agent to read/write/search the API:

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition, commands, usage |
| `scripts/memory_api.py` | Python client + CLI wrapper |

### collective-memory-curator

Memory hygiene companion:

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition, commands, usage |
| `scripts/validate.py` | Validate entry schema |
| `scripts/dedup.py` | Semantic dedup check |
| `scripts/sweep.py` | Weekly cleanup sweep |
| `scripts/reindex.py` | Rebuild index from entries |
| `scripts/sign.py` | Provenance signature stamp |
| `scripts/verify.py` | Verify signature |

Install: clone repo into any agent workspace, run `openclaw skills check` to register.
