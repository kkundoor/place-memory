# resolver redesign specification

## why this exists

The first live field-test round exposed failure modes that the clean 12-case resolver fixture set does not model. This document freezes those failures as requirements before production resolver behavior changes.

The product invariant remains:

> AI may interpret evidence, but it may not silently establish real-world identity.

The resolver must therefore prefer review or abstention over a false canonical place.

## target pipeline

```text
artifact
→ extract evidence
→ retrieve provider candidates
→ normalize structured fields
→ reject hard contradictions / incompatible entity classes
→ deduplicate records that represent the same real place
→ require sufficient independent evidence
→ score only evidence that actually exists
→ resolve / review / abstain
→ persist resolution provenance and pre-decision metrics
```

## field findings

| id | severity | finding | required invariant |
| --- | --- | --- | --- |
| R1 | critical | Manual Zingerman confirmation is later described as auto-resolution even though confidence 0.5732 < 0.76 and gap 0.0746 < 0.10. | `resolution_method` is first-class state; explanation text is derived from it, not inferred from `status`. |
| R2 | critical | Missing location/category currently receive 0.50 and contribute positive confidence. | Missing evidence contributes no positive evidence. |
| R3 | critical | Correct extra evidence can lower confidence because city text is compared to the entire formatted address. | Correct additional evidence must not make a correct candidate less eligible. |
| R4 | critical | A perfect name-only candidate can reach 0.80 and auto-resolve with no independent corroboration. | Auto-resolution requires at least two independent evidence types above policy floors, except explicitly defined strong-anchor cases. |
| R5 | critical | Category compatibility uses fuzzy string similarity; `bakery` receives substantial credit against `boundary`. | Category compatibility comes from a finite explicit crosswalk / allow-deny policy, never edit distance or embedding distance. |
| R6 | high | Commercial hints can surface boundary, census, railway, road, or administrative entities for review. | Hard entity-class eligibility runs before ranking. |
| R7 | high | DIA node + relation represent the same institution and collapse the ambiguity gap. | Equivalent OSM records are deduplicated before ambiguity policy. |
| R8 | high | Naive proximity/name dedup could merge two real nearby chain locations. | Dedup has a false-merge guard using structured address/type/provider identity evidence. |
| R9 | critical | Generic evidence such as “this coffee shop” is forced into a place name and searched globally. | Extraction may represent unknown identity; no identity anchor means abstain before provider search. |
| R10 | high | A road named “Coffee Shop Road” outranks real venues because name similarity dominates and category mismatch is weak. | Incompatible entity classes cannot win ranking regardless of name similarity. |
| R11 | high | Starbucks is blocked by both confidence and candidate separation; “ambiguity” alone does not explain the outcome. | Absolute evidence sufficiency and inter-candidate ambiguity are measured separately. |
| R12 | high | DIA exact-name candidates with correct city remain below threshold due feature construction. | At least one realistic two-signal, unique-place path must organically reach auto-resolution. |
| R13 | medium | Field export contains `CafÃ©` / `QuindÃ­o`, while browser rendering was correct. | Unicode is bisected at provider parse, model, SQLite, API serialization, and report/export boundaries. |
| R14 | high | There is no “none of these” review action. | Review UI/API supports explicit candidate rejection that returns the memory to abstained/unresolved state. |
| R15 | high | Provider-zero-candidate behavior exists only in clean synthetic tests, not real-field corpus. | Field corpus contains zero-candidate and provider-miss cases separately from resolver ranking failures. |
| R16 | high | Clean synthetic precision can hide live provider/resolver failures. | Evaluation reports synthetic and field corpora separately; neither metric substitutes for the other. |

## policy requirements

### evidence completeness

Auto-resolution eligibility is a gate, not a side effect of a blended confidence number.

Normal auto-resolution requires at least two independent evidence families, for example:

- name + structured location
- name + compatible category
- address + name
- address + structured location

Future strong-anchor exceptions such as an exact provider ID or explicit coordinates must be enumerated in policy rather than falling out of weights.

### category mechanism

Category compatibility must be discrete and inspectable. Provider tags map through an explicit table into product-level families.

Examples:

```text
shop=bakery        → bakery
amenity=cafe       → cafe
amenity=restaurant → restaurant
tourism=museum     → museum
leisure=stadium    → stadium

boundary=*         → non-venue
place=*            → administrative/geographic
highway=*          → road/transport
railway=*          → transport
```

A continuous string/embedding similarity is not allowed to determine whether an entity class is semantically eligible.

### location

Use structured provider fields when available. Whole-string similarity between `"Ann Arbor"` and a complete postal address is not an acceptable location feature.

Hard conflicts such as explicit Detroit evidence against a Chicago candidate prevent automatic resolution.

### deduplication

Deduplication runs before candidate-separation policy.

A merge may require:

- strongly matching normalized name,
- close coordinates,
- compatible entity family,
- no conflicting structured address,
- provider-record structure consistent with alternate representations of one entity.

A close same-name pair with conflicting house numbers must remain separate.

### provenance

Persist resolution provenance independently from final status:

```text
resolution_status: resolved | needs_review | unresolved
resolution_method: auto | manual | abstained | null
pre_resolution_confidence
pre_resolution_gap
```

`resolution_method=null` is valid while a memory is pending review.

Manual confirmation must not overwrite the resolver's pre-confirmation score or gap.

### evaluation

Keep two named corpora:

1. `synthetic`: small controlled cases for deterministic mechanics.
2. `field`: messy cases copied from real product runs.

Report each corpus separately. Field failures stay permanently after fixes.

## implementation order

1. land this specification and failing invariant tests
2. introduce structured evidence/provenance types
3. implement entity-class crosswalk and hard eligibility
4. implement structured location evidence
5. implement guarded deduplication
6. implement evidence-completeness gate
7. recalibrate ranking only after the above semantics are correct
8. add explicit reject-all review path
9. rerun field corpus
10. resume screenshot validation only after the resolver semantics pass
