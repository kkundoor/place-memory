# real-artifact pilot

This pilot is separate from the synthetic resolver suite and checked-in field regression fixtures.

Its job is to find the next real failure, not to produce an impressive accuracy number.

## local workspace

The runner reads `artifacts/real-pilot/manifest.json` and writes `artifacts/real-pilot/results.json`.

The whole `artifacts/real-pilot/` directory is gitignored so private screenshots do not enter the repository.

## labels

Keep externally verified ground truth separate from what the artifact itself supports.

Optional ground-truth provenance:

- `ground_truth_name`: the actual place the artifact came from, when independently known
- `ground_truth_city`: optional location context for that ground truth
- `ground_truth_source`: how the ground truth was externally verified
- `ground_truth_notes`: any additional provenance or ambiguity notes

Evaluation labels:

- `expected_extraction_name`: the specific place identity the artifact itself legitimately supports, or `null`
- `expected_candidate_names`: acceptable canonical retrieval candidates when a candidate expectation is justified
- `expected_mode`: `auto`, `review`, or `abstain`

Ground truth must not be copied into `expected_extraction_name` or `expected_candidate_names` merely because the answer is known externally. A known place can still be a correct extraction abstention when the artifact does not reveal its identity.

Do not label a case `auto` merely because the correct answer is known. `auto` means the artifact contains enough independent evidence that the resolver should be allowed to persist the identity without asking.

## stages

The runner reports separately:

1. extraction correctness
2. candidate recall@k on candidate-labeled cases
3. top-1 ranking accuracy conditional on successful retrieval
4. decision-mode correctness
5. false automatic resolution

Candidate recall and ranking use different denominators intentionally. If the correct candidate is never retrieved, that is a retrieval failure and lowers recall@k. It is not also counted as a ranking failure. Top-1 ranking is evaluated only for cases where the acceptable candidate was actually present in the retrieved set.

A correct candidate at rank 1 but wrong decision mode is a resolver-policy problem. A wrong extracted identity is an extraction problem. Ground-truth metadata is provenance only and does not change these labels or metrics.

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
