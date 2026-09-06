# evals

This project treats evals as part of the product, not a demo afterthought.

## resolution metrics

### top-1 place accuracy

How often the highest-ranked candidate is the actual saved place.

### false-confident rate

How often the system marks the wrong place as `resolved` instead of `needs_review` or `unresolved`.

This is the highest-cost failure. A miss is annoying; a wrong pin that looks certain breaks trust.

### review rate

How often a person has to confirm the candidate. The target is not zero. Review is the intended safety valve for ambiguity.

## retrieval metrics

After semantic retrieval is added:

- recall@3 for expected saved places
- nDCG@5 for ranked relevance
- structured-filter correctness

## feasibility metrics

- open / closed correctness when live hours are available
- route-duration error against the tool response: 0 by construction
- policy correctness for time-budget decisions
- `uncertain` rate when facts are missing

## system metrics

- p50 / p95 ingest latency
- p50 / p95 query latency
- tool error rate
- model / tool calls per request
- cost per ingest and query

## field data

Use `field-test-template.csv` during real use. Do not remove failures from the dataset after they are fixed; they become regression cases.
