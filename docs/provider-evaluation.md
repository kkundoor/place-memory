# place-search provider evaluation

## question

Can a free/no-key geocoder provide enough POI candidate recall for the core Place Memory entity-resolution path?

## first implementation: Nominatim

Nominatim was attractive because it is open-data-backed, needs no billing account, has a simple text search endpoint, and returns geographic candidates that can be normalized behind the same interface as other providers.

The client was implemented with:

- an explicit user agent
- a one-request-per-second minimum interval for the public service
- an in-memory duplicate-query cache
- typed normalization into the same `RawPlace` representation used by the resolver
- mock-transport contract tests

## live failure

On 2026-09-13, a known-positive business test used Carissa's in East Hampton. The following query variants all returned zero candidates:

- `Carissa's Bakery` + East Hampton + bakery
- `Carissa's The Bakery` + East Hampton + bakery
- `Carissa's The Bakery` + `221 Pantigo Road` + East Hampton + bakery
- `Carissa` + East Hampton + bakery

The important result was not that the resolver scored the wrong candidate. **No candidate reached the resolver at all.** Candidate-generation recall was the bottleneck.

## decision

Nominatim remains a useful no-key fallback/geocoder but is not treated as the primary commercial-POI authority.

The resolver was changed to depend on a provider-neutral `PlaceSearchClient` capability. That lets future candidate engines or providers replace Nominatim without rewriting scoring, confidence thresholds, review logic, persistence, or API behavior.

## next evaluation

The next provider/data-source comparison should measure candidate recall@k on the same labeled places before implementation is promoted into the main path. Candidate-source recall and resolver precision should remain separate metrics so a provider miss cannot be mistaken for a ranking failure.
