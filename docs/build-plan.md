# build plan

## critical path to first field test

```text
repo + contracts
      |
      v
save input --> extract hint --> resolve place --> confidence gate --> persist
                                                          |
                                                          v
browser location --> retrieve saved places --> live hours + route --> feasibility
                                                          |
                                                          v
                                                     field test
```

Anything that does not improve this path is below the line until the first test.

## day 1 - 2026-09-06

### done

- repository structure + architecture notes
- FastAPI service + local storage boundary
- Google Places resolution client
- confidence-scored resolver with ambiguity gate
- live hours + route-based feasibility rules
- React first-pass interface
- browser geolocation
- screenshot ingestion boundary for Vertex AI
- manual review/confirm path
- unit tests for resolver, retrieval, and feasibility
- initial Terraform API enablement
- field-test plan

### still needed before field test

1. configure one Google Cloud project
2. enable Vertex / Places / Routes APIs
3. set local credentials + maps key
4. run one real screenshot through extraction + resolution
5. run one real feasibility request from the browser
6. fix any setup or API-contract issues

## day 2 field test - 2026-09-07

Do not add features before the first 8-12 real saves are tested.

After the test, fix failures in this order:

1. false confident resolution
2. missing / wrong feasibility facts
3. retrieval miss
4. setup latency / tool failure
5. UI friction

## after first field test

### retrieval depth

- Vertex embeddings
- Cloud SQL Postgres + pgvector
- hybrid semantic + lexical + structured filters
- retrieval eval set and recall@k

### product depth

- map view with saved-place pins
- source provenance + evidence view
- better manual resolution UI
- bulk import adapters
- feedback capture

### production depth

- Cloud Run container
- private Cloud Storage
- Secret Manager
- least-privilege service account
- Cloud Build GitHub trigger
- Terraform for all resources
- structured trace events + latency / error metrics

## deliberately deferred

- generic recommendations from the open web
- unrestricted URL scraping
- fully autonomous agent loop
- multi-user collaboration
- social account login
- polished animations

The project should first prove that a personal save can be resolved correctly and turned into a grounded, useful decision in the real world.
