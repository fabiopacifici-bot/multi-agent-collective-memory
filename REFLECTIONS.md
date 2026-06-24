
# Reflections — Week 1

## Il codice fa quello che ho chiesto?

**Parzialmente.**

Il brief chiedeva un servizio di shared memory multimodale con RAG. L'implementazione copre:

- ✅ Database SQLite con la tabella `memories` e tutti i campi richiesti (agent, key, content_text, content_images, embedding, metadata)
- ✅ API REST completa: POST/PUT/GET/DELETE `/memory`, `/memory/search`, `/memory/recent`, `/memory/key/{key}`, `/embed`, `/health`
- ✅ Embedding multimodale via `EmbeddingService` (Qwen3-VL-Embedding-2B) con supporto testo + immagini Base64
- ✅ Ricerca semantica con cosine similarity in-memory
- ✅ Concorrenza gestita: `asyncio.Lock` sulle scritture, letture libere
- ✅ Bind su `0.0.0.0:8010`
- ✅ Dockerfile presente
- ⚠️ Il modello Qwen3-VL-Embedding-2B richiede hardware GPU — su CPU il fallback funziona ma è lento (~500ms); da verificare in deployment reale

## L'agente ha rispettato lo stack?

**Sì**, lo stack è stato rispettato:

| Componente | Richiesto | Implementato |
|---|---|---|
| Python 3.11+ | ✅ | ✅ (type hints moderni, `from __future__ import annotations`) |
| FastAPI | ✅ | ✅ (router, lifespan, dependency injection) |
| SQLite | ✅ | ✅ (`app/database.py`) |
| Qwen3-VL-Embedding-2B | ✅ | ✅ (`app/embedding.py`) |
| Docker | ✅ | ✅ (`Dockerfile`) |

L'agente ha aggiunto `asyncio.Lock` per la concorrenza (non esplicitamente richiesto nel brief ma corretto per FastAPI + SQLite).

## Cosa non era chiaro nel brief?

Il brief non specificava:

- Come gestire i **conflitti di chiave** su POST (upsert vs errore 409?) — l'implementazione ha scelto errore, che è più corretto REST ma potrebbe sorprendere chi usa il sistema
- Il **formato esatto della risposta** di `/memory/search` (solo campi memoria o anche il `score` di similarità?)
- Se il **Dockerfile** dovesse includere i pesi del modello o scaricarli al primo avvio — scaricarli all'avvio rallenta il cold start ma riduce la dimensione dell'immagine

## Cosa ho imparato sul briefing?

Specificare i **comportamenti di errore** (cosa restituisce l'API in caso di chiave duplicata, record non trovato, embedding fallito) è importante quanto specificare il happy path.

## Prossimo passo

Nel prossimo brief includerei:

- Una sezione **"Error responses"** per ogni endpoint con status code e payload atteso
- Un esempio concreto di **payload multimodale** (testo + immagine) per chiarire subito il formato Base64
- Indicare esplicitamente se i test devono usare mock dell'embedding model o il modello reale
