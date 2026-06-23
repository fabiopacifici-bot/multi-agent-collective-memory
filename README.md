# Multi-Agent Shared Memory Service

Tiny FastAPI microservice for shared multimodal memory across multiple agents.
It stores text/images plus embeddings in SQLite and exposes retrieval/search APIs over the network.

## Features

- Shared network-accessible memory API (no auth by design)
- Multimodal embedding support (text + image base64 payloads)
- CRUD endpoints for memory records
- Semantic search via cosine similarity over stored vectors
- SQLite persistence with concurrent reads and serialized writes
- Dockerized runtime (CUDA base image)
- CI/CD with GitHub Actions (tests + docker build + GHCR publish)

## Tech Stack

- Python 3.11+
- FastAPI
- SQLite
- Qwen/Qwen3-VL-Embedding-2B
- Docker

## API Endpoints

- `GET /health`
- `POST /embed`
- `POST /memory`
- `GET /memory/{id}`
- `GET /memory/key/{key}`
- `PUT /memory/{key}`
- `DELETE /memory/{key}`
- `GET /memory/recent?limit=10&agent=<optional>`
- `GET /memory/search?q=<query>&top_k=5`

Swagger UI is available at `/docs` once running.

## Quickstart (Local)

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the service:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4. Open:

- `http://localhost:8000/docs`
- `http://localhost:8000/health`

## Docker Run

The current Dockerfile starts uvicorn on port `8001`.

Build image:

```bash
docker build -t shared-memory-service:local .
```

Run CPU:

```bash
docker run --rm -p 8001:8001 shared-memory-service:local
```

Run GPU:

```bash
docker run --rm --gpus all -p 8001:8001 shared-memory-service:local
```

## CI/CD

Workflow file: `.github/workflows/ci-cd.yml`

### CI (all push/PR on main+dev)

- Setup Python 3.11
- Install dependencies from `requirements.txt`
- Run test suite with `pytest -v`
- Build Docker image (smoke build)

### CD (push on main or version tag `v*`)

- Login to GHCR using `GITHUB_TOKEN`
- Build and push image to:

`ghcr.io/<owner>/<repo>/shared-memory-service`

Published tags include branch/tag/sha and `latest` on default branch.

## Test

```bash
pytest -v
```

Notes:

- Tests use a deterministic dummy embedder in `tests/conftest.py` to avoid loading the full HF model during CI.
- Production runtime still loads the real model through app lifespan.

## Project Workflow

Branching and merge process is documented in `AGENT_FLOW.md`.

High-level:

- work from `dev`
- one isolated feature branch per route/feature
- commit frequently
- validate before merge
- merge `dev -> main` only after review

## Repository Structure

```text
app/
  main.py
  database.py
  embedding.py
  models.py
  routers/
    health.py
    embed.py
    memory.py
tests/
.github/workflows/
Dockerfile
requirements.txt
BRIEF.md
```
