# Brief

A tiny web service with REST API to store and retrieve shared information among agents in a multi-agent system. The service will be designed to be lightweight and efficient, allowing agents to quickly access and update shared data as needed.

## Obiettivo

Multimodal RAG shared memory over the network, with memory management and retrieval capabilities, to enable collaboration and coordination among agents in a multi-agent system.

## Stack scelto

- Python 3.11+
- FastAPI
- SQLite
- Qwen3-VL-Embedding-2B (multimodal embedding model)
- Docker

## Embedding Model: Qwen3-VL-Embedding-2B

- **Modello**: [Qwen/Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B)
- **Tipo**: Multimodal (testo + immagini + video)
- **Parametri**: 2B
- **Dimensione embeddings**: 1024 (configurabile 64–2048)
- **Context length**: 32K token
- **Hardware target**: GPU (CUDA) — inference in ~50ms su RTX 3060
- **Fallback**: CPU (più lento, ~500ms)
- **Dipendenze**: `transformers>=4.57.0`, `qwen-vl-utils>=0.0.14`, `torch>=2.0.0`, `numpy`, `Pillow`, `pydantic`

### Input supportati

- **Testo**: inviato come stringa JSON
- **Immagini**: codificate in **Base64** inline nel body JSON (no upload files)
- **Multi-modalità**: una singola richiesta può contenere testo + immagini — il modello produce un unico embedding congiunto

## Architettura del database (SQLite)

### Tabella `memories`

| Colonna | Tipo | Note |
|---------|------|------|
| id | INTEGER | PK, auto-increment |
| agent | TEXT | NOT NULL, indicizzato per lookup |
| key | TEXT | UNIQUE, chiave logica del record |
| content_text | TEXT | Contenuto testuale della memoria |
| content_images | TEXT | JSON array di immagini in Base64 (opzionale) |
| embedding | BLOB | Vettore di 1024 float32 (~4KB) |
| metadata | TEXT | JSON con metadati arbitrari |
| created_at | TIMESTAMP | Auto-impostato |
| updated_at | TIMESTAMP | Aggiornato su PUT |

### Indice semantico

- Similarità via **cosine similarity** calcolata in-memory
- Embedding deserializzati da BLOB a `numpy.ndarray`
- Per dataset grandi (>10K records): possibile introdurre FAISS in futuro

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
| DELETE | `/memory/{key}` | Rimuove una memoria per chiave logica |
| POST | `/embed` | Debug — embedding senza storage. Body: `{ "text": "...", "images": ["base64..."] }` → `{ "embedding": [...], "dim": 1024 }` |
| GET | `/health` | Health check — verifica caricamento modello |

### Concorrenza

- **Scritture** (`POST`, `PUT`, `DELETE`): protette da `asyncio.Lock` — una per volta
- **Letture** (`GET`): completamente concorrenti (no lock)
- **Embedding**: unico modello caricato in memoria all'avvio (`lifespan` event di FastAPI)

## Esposizione su rete

- Server bind su `0.0.0.0:8000`
- Container Docker EXPOSE 8000
- Agenti sulla stessa rete Docker (o host) possono chiamare `http://<host>:8000/memory/...`

### Docker & GPU CUDA

```dockerfile
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04
# Alternativa CPU-only: python:3.11-slim
```

Per eseguire con GPU:

```bash
docker run --gpus all -p 8000:8000 ...
```

Se GPU non disponibile, il modello fa automaticamente fallback su CPU.

## Componenti principali

1. API REST per la gestione della memoria condivisa
2. Modello multimodale Qwen3-VL-Embedding-2B per embeddings
3. Ricerca semantica per similarità (cosine similarity)
4. SQLite per persistenza (letture concorrenti, scritture seriali)
5. Docker per containerizzazione e esposizione su rete

## Vincoli

- No authentication
- Sharable over the network (bind 0.0.0.0)
- Lightweight and efficient
- GPU opzionale (fallback CPU)
- Immagini in Base64 inline (no file storage)

## Output atteso

- API REST documentata (Swagger/OpenAPI via FastAPI)
- Ricerca semantica multimodale (testo + immagini)
- CRUD completo su memoria condivisa
- Test unitari e di integrazione
- Dockerfile per containerizzazione

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
| 8 | `DELETE /memory/{key}` | `feature/8-delete` | ❌ | — |
| 9 | `POST /embed` | `feature/9-embed` | ❌ | — |
| 10 | Dockerfile | `feature/10-docker` | ❌ | — |

- Dockerfile per containerizzazione
