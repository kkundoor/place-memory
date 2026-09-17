# architecture

## product boundary

Place Memory is a **personal place-memory system**, not a generic recommendation engine. It starts from the user's own saved artifacts and tries to identify the real place behind each save.

The core safety rule is simple:

> model interpretation can create evidence, but it cannot create canonical identity by itself.

## current system

```text
                           ┌─────────────────────┐
                           │ React / TypeScript  │
                           └──────────┬──────────┘
                                      │
                               FastAPI boundary
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
                 ▼                    ▼                    ▼
        Gemini extraction      place resolution      retrieval /
        text + screenshot      + confidence gate     feasibility
                 │                    │                    │
                 │          ┌─────────┴─────────┐          │
                 │          ▼                   ▼          │
                 │      Google Places       Nominatim      │
                 │      when configured      fallback      │
                 │          │                   │          │
                 └──────────┴──── normalized ───┴──────────┘
                                      │
                                      ▼
                             SQLite memory store
                                      │
                        ┌─────────────┴─────────────┐
                        ▼                           ▼
                  React product UI            MCP adapter
```

## resolution boundary

`PlaceSearchClient` is a capability contract: given a `PlaceHint`, return normalized real-world place candidates.

The resolver does not know whether candidates came from Google, Nominatim, an open POI corpus, or a future provider. It only sees the internal `RawPlace` representation.

```text
provider response
      ↓
normalize
      ↓
RawPlace
      ↓
name similarity
location similarity
category similarity
      ↓
PlaceCandidate + provenance
      ↓
confidence + ambiguity gap
      ↓
resolved / needs_review / unresolved
```

That split matters because provider recall and resolver precision fail differently. A provider can return zero candidates even when the ranking logic is correct.

## why resolution is deterministic

Canonical identity is persisted and later affects retrieval, maps, routing, and feasibility. A confident hallucination therefore compounds into later answers.

The current resolver uses explicit weighted similarity plus two safety constraints:

- minimum confidence threshold
- minimum score separation from the second candidate

Ambiguous results go to review. Missing candidates remain unresolved.

The exact weights are still a baseline, not a final claim. They are measured by the checked-in resolver benchmark rather than treated as self-evidently correct.

## evidence and provenance

Each normalized candidate carries:

- provider
- provider-specific id
- name
- formatted address
- coordinates
- type/category evidence
- resolver score
- score components

The API exposes `GET /api/memories/{id}/resolution` so the final decision can be inspected rather than inferred from an opaque model response.

## model boundary

Gemini performs multimodal interpretation only:

```text
artifact → PlaceHint
```

A `PlaceHint` may contain supported name, city, address, category, and evidence. Unsupported details are not supposed to be invented by the extractor prompt.

The next extraction-level evaluation must use real screenshots and score model extraction separately from provider recall and resolver ranking.

## MCP boundary

The MCP server is an adapter over the deterministic application, not the owner of place identity.

Current tools expose:

- saved-place search
- memory lookup
- resolution explanation

This allows an external agent to consume grounded state while preserving the same confidence/review policy used by the UI and API.

## feasibility boundary

Feasibility remains deterministic and may return `uncertain` when live facts are unavailable.

It uses:

- resolved memory
- request-scoped current location
- time budget
- opening status when available
- route duration when available

The model never invents whether a place is open or how long travel takes.

## persistence

SQLite is intentionally retained for the first shareable single-user version. It already supports candidate snapshots and lightweight migration, and replacing it before the golden path is proven would add complexity without changing reviewer-visible behavior.

The next data-depth milestone is likely Postgres + PostGIS/pg_trgm/pgvector **only if** open-data candidate retrieval or hybrid retrieval demonstrates a concrete need.

## privacy and failure policy

- precise current location is request-scoped and not persisted by default
- normal request logs record ids/path/status/latency, not query text
- uploaded images have type and size limits
- API secrets live in environment variables, never source control
- confirmation trusts the stored candidate snapshot instead of client-supplied fields
- missing external facts produce `uncertain`, not fabricated certainty

## next architecture experiment

The highest-value next experiment is an open POI candidate engine:

```text
regional open POI corpus
        ↓
spatial + text candidate retrieval
        ↓
provider-neutral RawPlace candidates
        ↓
existing resolver
```

It should be adopted only if measured candidate recall improves enough to justify the additional data/indexing complexity.
