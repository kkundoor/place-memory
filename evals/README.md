# evaluation

Place Memory keeps evaluation close to the resolver because a wrong canonical identity is more damaging than asking for review.

## corpora

### synthetic

`python evals/run_resolution_eval.py`

The original deterministic fixture suite covers clean resolver mechanics: exact names, typos, chain ambiguity, address disambiguation, category conflicts, abbreviations, same-name places in different cities, and missing candidates.

Current published numbers remain fixture-level only:

- 12 cases
- 75% top-1 accuracy on labeled cases
- 100% precision among automatic resolutions
- 83.3% recall on cases labeled safe to auto-resolve
- 0% false auto-resolution rate
- 58.3% review/abstain rate

These numbers are not a claim about live artifact accuracy.

### field

`python evals/run_field_resolution_eval.py`

The field corpus is copied from actual product runs and is intentionally messy. It currently includes:

- typo-tolerant Zingerman retrieval
- Starbucks branch ambiguity
- Carissa's provider miss returning geographic entities
- duplicate OSM representations of Detroit Institute of Arts
- generic “coffee shop” evidence producing irrelevant global candidates

Field metrics are reported separately from synthetic metrics. A clean synthetic number must never substitute for field behavior.

## redesign invariant suite

The resolver redesign is driven by:

`python -m pytest evals/spec_tests/test_resolver_redesign_spec.py -q`

Before the redesign lands, this suite is expected to expose current failures. It is intentionally outside the default `api/pytest.ini` test path so main CI stays green while the redesign is developed on a branch.

The invariants cover:

- no name-only auto-resolution
- evidence monotonicity
- explicit category crosswalk
- hard entity-class eligibility
- guarded duplicate collapse
- first-class resolution provenance
- identity abstention before provider search
- conflicting-location safety
- reachable realistic auto-resolution
- Unicode bisection checks
- explicit “none of these” review path

## primary safety metric

The primary safety metric remains false automatic resolution rate. Review and abstention are expected outcomes, not failures by themselves.

Failures remain in their corpus after fixes so they become permanent regression cases.
