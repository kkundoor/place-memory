# place memory

A personal geospatial memory that turns noisy saved artifacts — screenshots, notes, links, and captions — into grounded real-world places without letting the LLM silently invent identity.

The project is intentionally narrow: the interesting problem is **reliable entity resolution under incomplete evidence**, not another general chatbot.

## what it does

```text
artifact
  ↓
Gemini multimodal extraction
  ↓
structured place hint + evidence
  ↓
provider-neutral place search
  ↓
normalized candidates
  ↓
deterministic resolver
  ↓
resolved / needs_review / unresolved
  ↓
persisted memory + provenance
  ↓
retrieval + grounded feasibility checks
```

The LLM interprets artifacts. It does **not** establish canonical place identity. Identity is decided by explicit candidate scoring, confidence thresholds, ambiguity checks, and user review when evidence is weak.

## why this is not an LLM wrapper

The core engineering work is outside the model call:

- provider-neutral place-search interface
- normalization into one internal candidate model
- fuzzy name, location, and category scoring
- explicit confidence and ambiguity policy
- abstention instead of fabricated certainty
- persisted candidate provenance and review state
- deterministic explanation endpoint for every resolution
- labeled resolver benchmark used as a CI safety gate
- agent-facing MCP tools layered over the deterministic system rather than putting an agent in charge of identity

## current resolver benchmark

`python evals/run_resolution_eval.py`

Current deterministic fixture-level results:

| metric | result |
| --- | ---: |
| labeled cases | 12 |
| top-1 accuracy on labeled targets | 75.0% |
| automatic-resolution precision | 100.0% |
| recall on cases labeled safe to auto-resolve | 83.3% |
| false automatic resolution rate | 0.0% |
| review / abstain rate | 58.3% |

The benchmark intentionally includes typos, same-name businesses in different cities, chain ambiguity, conflicting category evidence, incomplete names, and missing candidates. CI fails if a benchmark case produces a false automatic resolution.

These are **resolver-level fixture metrics**, not a claim about real-world end-to-end accuracy. Screenshot extraction and live provider recall are evaluated separately because collapsing them into one number hides where failures occur.

## an engineering failure that changed the design

The first no-key POI candidate source was Nominatim/OpenStreetMap. It integrated cleanly and passed request/normalization tests, but live validation against a known real business returned no candidates even with exact-name and address variations.

That failure exposed a useful boundary: provider coverage and resolver quality are separate problems. The resolver now depends on a `search_places` capability instead of a concrete vendor, so candidate sources can change without rewriting the confidence policy. Nominatim remains a rate-limited no-key fallback/geocoder, not a claim of production-grade commercial POI coverage.

See [`docs/provider-evaluation.md`](docs/provider-evaluation.md).

## stack

- **frontend:** React + TypeScript + Vite
- **API:** Python + FastAPI + Pydantic
- **multimodal interpretation:** Gemini Developer API
- **place grounding:** provider-neutral client; Google Places when configured, Nominatim fallback for no-key development
- **persistence:** SQLite with lightweight schema migration
- **matching:** RapidFuzz + explicit resolver policy
- **agent/tool interface:** optional MCP server
- **testing:** pytest + httpx mock transports + resolver benchmark
- **CI:** GitHub Actions for API tests, resolver safety eval, MCP import smoke test, and frontend production build
- **local runtime:** Docker Compose or direct Python/Node processes

## run locally

### fastest: Docker Compose

The repository is runnable without paid infrastructure. Copy the example environment and start both services:

```bash
cp .env.example .env
docker compose up --build
```

Then open `http://localhost:5173`.

Without API keys, text saves still run through the deterministic pipeline using fallback extraction and Nominatim candidate search. Screenshot extraction requires `GEMINI_API_KEY`. Google Places/Routes are optional and only used when `GOOGLE_MAPS_API_KEY` is configured.

Never commit `.env`.

### run without Docker

Backend:

```bash
cd api
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd web
npm ci
npm run dev
```

## zero-cost deployment path

The root `Dockerfile` builds the frontend and API into a single container so the hosted demo does not need cross-origin wiring. `render.yaml` is included as a free-tier deployment blueprint.

The hosted demo intentionally uses ephemeral SQLite storage; it is for evaluation/demo use, not production durability. Screenshot extraction also requires adding `GEMINI_API_KEY` as a host secret. No secret belongs in the repository.

The current repository does not claim an always-on paid deployment. The Docker image is the portable deployment artifact; the optional Terraform directory documents a later GCP boundary without provisioning paid data resources.

## MCP tools

The MCP layer deliberately exposes the grounded system instead of making place identity agentic.

```bash
cd api
pip install -r requirements-mcp.txt
python -m app.mcp_server
```

Current tools:

- `search_saved_places(query)`
- `get_place_memory(memory_id)`
- `explain_place_resolution(memory_id)`

The boundary is intentional: an agent can consume Place Memory as a tool, but the agent cannot bypass the resolver's confidence/review policy.

## API highlights

- `POST /api/memories/ingest` — extract and resolve a text/link save
- `POST /api/memories/ingest-image` — multimodal screenshot ingestion
- `POST /api/memories/{id}/confirm` — confirm one of the stored review candidates
- `GET /api/memories/{id}/resolution` — inspect policy, scores, gaps, provenance, and candidates
- `POST /api/feasible` — deterministic `yes / no / uncertain` decision using available routing/hours facts

## design principles

1. **interpretation is not truth** — model output is evidence, not canonical identity.
2. **abstention is a feature** — ambiguous places go to review rather than being silently persisted.
3. **external systems sit behind boundaries** — provider-specific response formats do not leak into resolver logic.
4. **measure safety, not vibes** — false confident resolution is treated as the highest-cost failure.
5. **agentic only where it helps** — MCP exposes deterministic capabilities; it does not replace inspectable domain logic.
6. **preserve failure history** — provider misses and benchmark regressions remain documented instead of being edited out of the story.

## current limitations / next depth layer

The current shareable version still has deliberate limits:

- Nominatim is not sufficient as the long-term commercial POI source.
- the checked-in benchmark measures resolver behavior with labeled candidate fixtures, not full real-world screenshot accuracy.
- SQLite is appropriate for the current single-user local version; it is not the intended long-term geospatial/search store.
- Google-backed routing/hours are unavailable without Google credentials, so feasibility safely returns `uncertain` when live facts are missing.

The next technical milestone is an open-data candidate engine using a regional POI corpus, then measuring it against a live provider before deciding whether PostGIS/pg_trgm/pgvector or an additional provider materially improves recall.

## repository map

```text
api/app/clients/        external model/place clients
api/app/services/       resolver, retrieval, feasibility policy
api/app/storage/        persistence
api/app/mcp_server.py   agent-facing tool adapter
evals/                  labeled resolver benchmark and results
web/                    React product surface
docs/                   architecture and decision history
```
