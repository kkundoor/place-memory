# evaluation

Place Memory treats evaluation as part of the resolver, not as a demo afterthought. A wrong canonical place is more damaging than asking the user for review, so the primary safety metric is **false auto-resolution rate**.

## resolver benchmark

`python evals/run_resolution_eval.py` runs a labeled, deterministic resolver-level benchmark covering exact names, typos, chain ambiguity, address disambiguation, category conflicts, abbreviations, same-name places in different cities, and missing candidates.

Current fixture-level results:

- 12 labeled cases
- 75% top-1 accuracy on cases with a labeled target
- 100% precision among automatic resolutions
- 83.3% recall on cases intentionally labeled safe to auto-resolve
- 0% false auto-resolution rate
- 58.3% review/abstain rate

The script exits non-zero if any false automatic resolution appears, so the safety policy can be used as a CI gate.

These are **resolver-level fixture metrics**, not a claim about end-to-end real-world accuracy. The next benchmark layer uses real screenshots and live candidate providers and measures extraction accuracy, provider recall@k, latency, and cost separately.

## why abstention is intentional

The resolver has three outcomes:

- `resolved`: confidence and candidate separation pass policy
- `needs_review`: at least one candidate exists, but evidence is not strong enough for automatic canonicalization
- `unresolved`: no candidate exists

The target is not a zero review rate. Review is the safety valve for ambiguous saves, especially chain locations and incomplete social artifacts.

## future system metrics

For live artifact evaluation:

- extraction correctness
- candidate recall@1 / recall@5
- automatic-resolution precision and recall
- false auto-resolution rate
- review/abstention rate
- p50 / p95 ingest latency
- provider/model error rate
- model and tool calls per request
- approximate cost per ingest and query

Failures stay in the dataset after fixes so they become regression cases.
