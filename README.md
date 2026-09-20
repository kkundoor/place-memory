# place-memory

**Live demo:** https://place-memory-caxs.onrender.com

A small app for turning messy place saves — screenshots, notes, captions, and links — into grounded real-world places.

The hosted demo runs the real extraction → candidate retrieval → resolver path for notes and screenshots, but deliberately does not persist visitor inputs or results to Place Memory storage. Fixed regression examples underneath show resolve, review, and abstain behavior.

The main constraint is simple: **the model can interpret evidence, but it does not get to declare a place identity by itself.**

## how it works

```text
saved artifact
→ Gemini extracts a place hint from visible / provided evidence
→ a place-search provider returns candidates
→ candidates are normalized, filtered, enriched, and deduplicated
→ a deterministic resolver decides:
   resolved / needs review / unresolved
→ in the persistent local app, the decision, candidates, score, gap, and method are stored
```

The resolver uses explicit evidence such as name, location, category, candidate separation, and provider-backed aliases. Weak or conflicting evidence goes to review or abstains instead of being silently saved as fact.

## why the resolver is separate from the model

The first version relied too much on fuzzy matching and clean examples. Real tests exposed problems quickly:

- a generic "coffee shop" note could produce junk global candidates
- duplicate OSM records could make one real place look ambiguous
- missing evidence could still add confidence
- a manual confirmation could later look like an automatic decision
- roads and boundaries could survive into place review
- renamed places could look like weak string matches even when the old name was valid

Those failures changed the design.

The current resolver has:

- an explicit no-identity abstention path
- hard filtering for incompatible entity classes
- duplicate collapse before ambiguity is measured
- separate `auto`, `manual`, and `abstained` provenance
- preserved pre-confirmation score and candidate gap
- a finite category compatibility table rather than fuzzy category matching
- independent-evidence requirements for automatic resolution
- provider-backed alternate / historical names
- an explanation endpoint that exposes the evidence used for each decision

## one real example

A TikTok screenshot contained a small `STOW LAKE` logo, a San Francisco location tag, and text about renting a pedal boat.

On the first live run, the system retrieved the current `Blue Heron Lake` record but only scored it at `0.6471`, mixed in road objects, and correctly required manual confirmation.

That run exposed three separate issues:

1. `Stow Lake` is a historical name for the current place
2. "boat rental" described an activity, not the identity type of the lake
3. road objects should not survive as place candidates

After fixing those issues, the same screenshot was run again. The saved explanation showed:

```text
canonical place: Blue Heron Lake
resolution method: auto
match score: 1.0
name source: alias:Stow Lake
location: 1.00
category: 1.00
```

The before/after run is documented in [`docs/field-test-2026-09-17.md`](docs/field-test-2026-09-17.md).

The current input path also preserves the original screenshot alongside the interpreted result. Text can be supplied with the image as extra context, but it remains stored separately from the model's extracted evidence. A saved screenshot was live-tested through a backend restart to verify that the artifact and memory remain linked.

## evaluation

I keep controlled resolver tests separate from live product evidence.

### synthetic resolver cases

```bash
python evals/run_resolution_eval.py
```

Current fixture results:

| metric | result |
| --- | ---: |
| cases | 12 |
| top-1 accuracy on labeled cases | 100% |
| automatic-resolution precision | 100% |
| recall on cases labeled safe to auto-resolve | 100% |
| false automatic resolution rate | 0% |
| review / abstain rate | 50% |

### field regression scenarios

```bash
python evals/run_field_resolution_eval.py
```

Current fixture results:

| metric | result |
| --- | ---: |
| distinct scenarios | 6 |
| decision-mode accuracy | 100% |
| top-1 accuracy on labeled cases | 100% |
| false automatic resolution rate | 0% |

These are small regression sets, not a claim about production accuracy. The next evaluation pass is a curated set of real artifacts with stage-level labels for extraction, candidate recall, ranking, decision mode, and false automatic resolution.

See [`evals/README.md`](evals/README.md).

## stack

- React + TypeScript + Vite
- FastAPI + Pydantic
- Gemini Developer API for text / screenshot interpretation
- Photon for no-key candidate search
- Nominatim `/lookup` for OSM alias metadata
- RapidFuzz + explicit resolver policy
- SQLite + local artifact storage
- optional MCP adapter
- pytest + GitHub Actions
- Docker / Docker Compose

Google Places / Routes remain optional. Routing uses destination coordinates so a Photon/OSM ID is never passed to Google as if it were a Google place ID. Opening-hours lookup only runs when a compatible Google place identity exists; otherwise the result stays unknown.

## local setup

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:5173`.

Screenshot extraction requires `GEMINI_API_KEY`. Google credentials are optional.

### direct processes

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

## API highlights

- `POST /api/memories/ingest`
- `POST /api/memories/ingest-image`
- `GET /api/memories/{id}/source-image`
- `POST /api/memories/{id}/confirm`
- `POST /api/memories/{id}/reject`
- `GET /api/memories/{id}/resolution`
- `POST /api/feasible`

## current limits

This is still an engineering prototype, not a production service.

- screenshot storage is local filesystem storage behind a small storage boundary; it is not a durable cloud-object-store design
- the real-artifact evaluation set is still small
- provider recall is not yet measured on a broad enough real set to justify more retrieval infrastructure
- opening-hours data is unavailable when there is no compatible status-provider identity
- SQLite + local files are appropriate for the current local single-user version, not multi-user production storage
- a public deployment would need user isolation before accepting private screenshots

The next pass is the **curated real-artifact pilot**, followed by fixes only where that pilot exposes a real gap.
