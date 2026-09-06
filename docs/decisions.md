# decisions

## 001 - resolve before retrieval

**decision:** unresolved artifacts can be stored, but they are not treated as canonical places.

**why:** a false confident place match is worse than an unresolved save. The product only becomes useful if the map and feasibility answers are trustworthy.

## 002 - typed tool flow over free-form agent loop

**decision:** v1 uses explicit Python services and typed tool boundaries instead of giving an LLM arbitrary control.

**why:** easier to test, trace, and explain. We can add a planner later without coupling the core place logic to one agent framework.

## 003 - sqlite locally, postgres in cloud

**decision:** keep the repository interface database-agnostic on day 1.

**why:** tomorrow's field test should not depend on cloud provisioning. Production still targets Cloud SQL Postgres + pgvector.

## 004 - maps apis own facts

**decision:** Places and Routes own canonical place ids, hours, distance, and travel duration.

**why:** these are externally verifiable facts. The model should interpret messy user artifacts, not guess operational data.

## 005 - accuracy before ingestion breadth

**decision:** screenshot/text/note plus optional source url is enough for the first test.

**why:** supporting every social platform before measuring place-resolution quality would hide the core risk behind integration work.
