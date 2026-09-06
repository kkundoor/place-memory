# place memory

A personal geospatial memory for the places buried in screenshots, links, notes, and social saves.

The goal is simple: save something once, resolve the real place behind it, then later ask questions like:

- what did I save near me?
- which saved spots are actually doable in the next two hours?
- show me coffee or lunch places I saved around here

The first version is deliberately narrow. It prioritizes **correct place resolution** and **grounded feasibility checks** over broad ingestion support.

## v1 flow

`save -> extract hint -> resolve place -> store evidence -> retrieve -> check feasibility`

The LLM is used for interpretation. Place identity, hours, routing, and feasibility are grounded in deterministic tools and explicit rules.

## stack

- React + TypeScript frontend
- Python + FastAPI API
- Google Places / Routes for place grounding and travel time
- Vertex AI for multimodal extraction and query parsing
- SQLite locally; Cloud SQL Postgres + pgvector planned for deployment
- Cloud Run + Terraform + Cloud Build planned for GCP deployment

## local setup

```bash
cd api
python -m venv .venv
source .venv/bin/activate  # windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Then in another terminal:

```bash
cd web
npm install
npm run dev
```

The API runs without Google credentials in local stub mode. Real place resolution and routing require the Google Maps APIs to be configured.

## status

Day 1 build. See `docs/field-test-2026-09-07.md` for the first real-world test plan.
