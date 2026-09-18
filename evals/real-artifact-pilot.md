# real-artifact pilot

This pilot is separate from the synthetic resolver suite and checked-in field regression fixtures.

Its job is to find the next real failure, not to produce an impressive accuracy number.

## local workspace

The runner reads `artifacts/real-pilot/manifest.json` and writes `artifacts/real-pilot/results.json`.

The whole `artifacts/real-pilot/` directory is gitignored so private screenshots do not enter the repository.

## labels

Label each case before looking at the system result when possible:

- `expected_extraction_name`: the specific place identity the artifact actually supports, or `null`
- `expected_candidate_names`: acceptable canonical candidates
- `expected_mode`: `auto`, `review`, or `abstain`

Do not label a case `auto` merely because the correct answer is known. `auto` means the artifact contains enough independent evidence that the resolver should be allowed to persist the identity without asking.

## stages

The runner reports separately:

1. extraction correctness
2. candidate recall@k
3. correct-candidate rank
4. decision-mode correctness
5. false automatic resolution

A miss at stage 2 is a retrieval problem. A correct candidate at rank 1 but wrong decision mode is a resolver-policy problem. A wrong extracted identity is an extraction problem.

## target set

Aim for roughly 12–15 real artifacts chosen for failure-mode coverage:

- exact unique place
- typo / paraphrase
- same-brand branch ambiguity
- generic identity / insufficient identity
- provider miss
- duplicate provider representation
- historical alias
- wrong-city contradiction
- category/entity mismatch
- venue within venue
- insufficient screenshot evidence
- accented / Unicode place
- partial or logo-only identity
- conflicting image + user context

The same artifact should not be duplicated just to inflate the corpus.
