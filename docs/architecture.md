# architecture

## product boundary

The system is a **personal place-memory layer**, not a generic local search engine.

It should answer from the user's own saves first. External place APIs are used to identify and verify those saves, not to silently replace them with generic recommendations.

## v1 dependency graph

```text
source artifact
    |
    v
extractor ---------> structured place hint
    |                         |
    |                         v
    |                  place resolver -------> Google Places
    |                         |
    |                         v
    +-----------------> evidence record
                              |
                              v
                         memory store
                         /          \
                        v            v
                 retrieval       feasibility -------> Google Routes
                        \            /
                         v          v
                           response
```

The field test only depends on the vertical path from ingestion through resolution, storage, retrieval, and feasibility. Auth, bulk import, social scraping, and a polished map do not block it.

## design rules

### 1. extraction is not truth

The model can infer a place name, neighborhood, category, or address from an artifact. Those are hints only.

A place becomes resolved only after a tool-backed candidate passes the confidence gate. Low-confidence or ambiguous results stay unresolved and require review.

### 2. feasibility is deterministic

The model does not invent whether a place is open or how long it takes to get there.

Feasibility uses:

- resolved place id
- current location
- current time
- requested time budget
- live opening-hours data when available
- live route duration when available

The result is `yes`, `no`, or `uncertain`, with reasons.

### 3. current location is request-scoped

Current location is used to answer the current query and is not persisted by default.

### 4. raw artifacts stay private

Production target:

- private Cloud Storage bucket for uploaded artifacts
- Cloud Run service account with least-privilege access
- secrets in Secret Manager
- no raw screenshot text or precise location in normal application logs

## target gcp architecture

```text
React web
   |
   v
Cloud Run API
   |--- Vertex AI              extraction / query parsing / embeddings
   |--- Google Places          canonical place identity / hours
   |--- Google Routes          travel time / distance
   |--- Cloud SQL Postgres     memories + structured metadata + pgvector
   |--- Cloud Storage          private source artifacts
   |--- Secret Manager         API secrets
   |
Cloud Logging / trace metadata (ids, latency, tool result status; no raw private content)
```

Terraform owns infrastructure. Cloud Build runs tests and deploys from GitHub after the local vertical slice is stable.

## later, not day 1

- direct TikTok / Instagram / Reddit ingestion
- Google Maps saved-list import
- bulk background processing
- pgvector + hybrid ranking
- map clustering
- multi-user auth
- MCP exposure
- agent runtime / richer tool planner
