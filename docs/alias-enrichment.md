# alias enrichment

## problem

A saved artifact may contain a valid historical or alternate name while the search provider returns the current canonical name. Pure edit-distance ranking treats that as a weak name match even when both names refer to the same real entity.

The first live screenshot exposed this with `Stow Lake` in the artifact and `Blue Heron Lake` in current candidate data.

## design

Candidate generation remains Photon-first. For returned OSM objects, a metadata adapter may look up alternate names using the stable OSM object ID. The resolver then compares the artifact name against both the canonical name and provider-backed aliases.

Alias evidence does not bypass the safety policy. Automatic resolution still requires independent corroboration such as structured location/category evidence and candidate separation.

## current metadata source

The local/demo path uses Nominatim's `/lookup` endpoint with `namedetails=1`, which can return language variants, alternate names, and older names. Requests are batched, cached in memory, carry an identifying User-Agent, and share the client's one-request-per-second limiter.

Alias enrichment is deliberately non-fatal: if the metadata lookup is unavailable, Photon candidates still flow into the resolver unchanged.

The public Nominatim service is not a production dependency. A scaled deployment should replace this adapter with a self-hosted/open-data index or another provider while keeping the same enrichment boundary.
