# evaluation

The resolver is evaluated separately from the model and the place-search provider so a failure can be assigned to the right stage.

## three kinds of checks

### synthetic resolver cases

`python evals/run_resolution_eval.py`

Small controlled cases for mechanics such as:

- exact names
- typos
- same-name places in different cities
- chain ambiguity
- category conflicts
- incomplete evidence
- missing candidates

### resolver invariants

`python -m pytest evals/spec_tests/test_resolver_redesign_spec.py -q`

These protect behaviors discovered through field failures, including:

- missing evidence does not add confidence
- automatic resolution needs independent evidence
- incompatible entity classes are filtered before ranking
- duplicate provider records do not create false ambiguity
- generic identity descriptions abstain before search
- manual confirmation is represented separately from automatic resolution
- wrong-city evidence blocks automatic resolution
- Unicode survives normalization and persistence
- review has an explicit "none of these" path

### field regression scenarios

`python evals/run_field_resolution_eval.py`

These are repeatable fixtures distilled from actual product runs.

Current scenario types:

1. Zingerman's typo + ambiguity
2. Starbucks branch ambiguity
3. Carissa's provider miss
4. Detroit Institute of Arts duplicate records
5. generic coffee-shop abstention
6. Stow Lake historical-name resolution

The field corpus is not a continuously appended live database export. Live captures are versioned separately, then important failures are turned into stable regression scenarios.

## alias collision

Alias support creates its own failure mode: more than one real candidate can share the same historical or alternate name.

A controlled regression case therefore checks that two equally plausible candidates sharing an alias remain in review. Alias evidence is not allowed to bypass the candidate-separation rule.

## next real-artifact pilot

The next evaluation pass is a curated set of roughly 12–15 real artifacts selected for failure-mode coverage rather than raw size.

Target scenarios include:

- exact unique place
- typo / paraphrase
- same-brand branch ambiguity
- generic identity
- provider miss
- duplicate provider representations
- historical alias
- wrong-city contradiction
- category mismatch
- venue within venue
- insufficient screenshot evidence
- accented / Unicode name
- partial or logo-only identity
- conflicting artifact/context evidence

For each artifact, record the stages separately:

```text
extraction correct?
correct candidate retrieved?
rank of correct candidate?
expected decision: auto / review / abstain?
observed decision correct?
false automatic resolution?
```

That keeps extraction quality, candidate recall, ranking, and decision policy from being collapsed into one misleading number.
