# decisions

## 001 - resolve before treating a save as canonical

**decision:** unresolved artifacts may be stored, but they are not treated as canonical places.

**why:** a false confident place match is worse than an unresolved save because later retrieval/routing decisions inherit the error.

## 002 - typed tool flow over a free-form agent loop

**decision:** core place resolution uses explicit services and typed boundaries.

**why:** canonical identity needs inspectable, testable behavior. Agentic clients can consume the result through MCP without bypassing the safety policy.

## 003 - keep SQLite for the first shareable single-user version

**decision:** do not migrate persistence simply to add infrastructure keywords.

**why:** SQLite already supports the current scale, tests, candidate persistence, and local run path. Postgres/PostGIS is reserved for a measured retrieval/indexing need.

## 004 - separate model interpretation from external facts

**decision:** Gemini extracts supported clues; providers/routing systems own real-world identity and operational facts.

**why:** the model should not guess addresses, opening status, or travel time.

## 005 - provider-neutral place search

**decision:** the resolver depends on `PlaceSearchClient`, not on Google or Nominatim directly.

**why:** live testing showed that provider coverage can fail independently of ranking logic. Switching candidate sources should not require rewriting the resolver.

## 006 - keep Nominatim as fallback, not POI authority

**decision:** Nominatim remains useful for no-key development/geocoding but is not presented as sufficient commercial-POI coverage.

**why:** a known-positive business test returned zero candidates across exact-name and address variants. The failure occurred before ranking.

## 007 - provenance is part of the candidate model

**decision:** candidates carry provider and provider-specific identity in addition to normalized fields.

**why:** future multi-source resolution, debugging, and explanation are difficult if source identity is discarded at ingestion.

## 008 - false auto-resolution is the primary resolver safety metric

**decision:** CI gates on the checked-in labeled resolver benchmark producing zero false automatic resolutions.

**why:** review is acceptable friction; silently persisting the wrong canonical place breaks trust and contaminates later decisions.

## 009 - MCP is an adapter, not the resolution engine

**decision:** expose deterministic search/memory/explanation capabilities through MCP rather than converting identity resolution into an agent loop.

**why:** this provides an agent-tool integration surface without making a safety-sensitive decision less inspectable.

## 010 - no Kafka/Kubernetes/Redis until a measured problem requires them

**decision:** do not add distributed infrastructure for portfolio signaling alone.

**why:** current workload does not require high-throughput event replay, cluster orchestration, or a job queue. If ingestion latency/failure behavior later justifies asynchronous processing, the architecture can add a worker/queue with a concrete reason.
