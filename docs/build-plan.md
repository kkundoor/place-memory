# build plan

## shareable checkpoint

The first-share bar is intentionally narrower than the eventual research/depth target.

### required before sharing

- real text/screenshot ingestion boundary
- Gemini Developer API extraction path
- provider-neutral candidate search
- deterministic confidence + ambiguity policy
- review / abstention behavior
- persisted candidates + provenance
- explanation endpoint
- resolver benchmark used as CI safety gate
- optional MCP adapter over deterministic capabilities
- reproducible local startup
- backend tests + frontend production build in CI
- README that states current limitations honestly

### already implemented in this checkpoint

- API + React product surface
- screenshot type/size validation
- local persistence + candidate migration
- request tracing without query text
- bounded feasibility concurrency
- provider-client contract tests
- no-key Nominatim fallback with rate limiting/cache
- provider-neutral resolver boundary
- provenance fields
- resolution explanation endpoint
- deterministic 12-case resolver benchmark
- MCP adapter
- Docker Compose local runtime

## next depth milestone

Do not add infrastructure by default. Use measurements to choose the next subsystem.

### candidate-generation experiment

1. build a small open-data POI prototype
2. evaluate candidate recall@k against a labeled real-place set
3. compare with a live provider
4. keep multi-source retrieval only if it improves recall enough to justify complexity

### real artifact benchmark

Separate the pipeline into three measured stages:

1. **extraction:** did the screenshot produce supported clues?
2. **candidate generation:** did the correct place appear in top-k?
3. **resolution:** given candidates, did the policy resolve/review correctly?

Track latency, provider/model errors, and approximate cost in addition to accuracy.

### infrastructure only when earned

- Postgres/PostGIS/pg_trgm if local POI/search indexing needs it
- pgvector if semantic retrieval beats lexical/structured baselines
- Redis worker if synchronous ingestion latency/retry behavior becomes a real product problem
- hosted deployment once a zero-cost provider/account is connected

## interview hardening after share

Once the repository is circulating, shift from implementation speed to ownership:

- explain every major boundary from first principles
- reproduce the Nominatim failure and provider decision
- defend the resolver metrics/thresholds
- diagnose injected failures without copy-paste
- explain HTTP/TCP/TLS, async/concurrency, DB indexing, Docker, CI, secrets, and retry/idempotency concepts where they appear in the project
