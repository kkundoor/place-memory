# evaluation

Place Memory keeps evaluation close to the resolver because a wrong canonical identity is more damaging than asking for review.

## corpora

### synthetic

`python evals/run_resolution_eval.py`

The deterministic fixture suite covers clean resolver mechanics: exact names, typos, chain ambiguity, address disambiguation, category conflicts, abbreviations, same-name places in different cities, and missing candidates.

These numbers are fixture-level only; they are not a claim about live artifact accuracy.

### field

`python evals/run_field_resolution_eval.py`

The field corpus is copied from actual product runs and intentionally preserves messy behavior. It currently covers:

- typo-tolerant Zingerman retrieval
- Starbucks branch ambiguity
- Carissa's provider miss returning geographic entities
- duplicate OSM representations of Detroit Institute of Arts
- generic “coffee shop” evidence producing irrelevant global candidates
- a screenshot whose visible historical name `Stow Lake` maps to the current canonical `Blue Heron Lake`

Field metrics are reported separately from synthetic metrics. A clean synthetic number must never substitute for field behavior.

## redesign invariant suite

`python -m pytest evals/spec_tests/test_resolver_redesign_spec.py -q`

The invariant suite covers evidence sufficiency, monotonicity, explicit category semantics, entity-class eligibility, guarded deduplication, first-class resolution provenance, identity abstention, location conflicts, reachable auto-resolution, Unicode handling, and explicit candidate rejection.

## alias / historical-name regression

Provider search results may use a current canonical name while a saved artifact contains a historical or alternate name. Candidate metadata can therefore include aliases sourced separately from search ranking. Resolver name scoring considers those aliases but still requires independent corroboration such as location or category before automatic resolution.

The live provider-enrichment path is optional and non-fatal: if alias metadata is unavailable, candidate search continues without it.

## primary safety metric

The primary safety metric remains false automatic resolution rate. Review and abstention are expected outcomes, not failures by themselves.

Failures remain in their corpus after fixes so they become permanent regression cases.
