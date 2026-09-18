# field test - 2026-09-17

## environment

- branch: `resolver-redesign-spec`
- commit: `67655d832e03be753e1f252c0cb6a0878f97fda1`
- candidate provider: Photon
- Gemini extraction: enabled
- Google Maps/routing: disabled

## live cases

### anonymous coffee-shop note

Input contained a generic coffee-shop description with no actual identity anchor.

Result:

- status: `unresolved`
- method: `abstained`
- candidates: 0

This validates the no-identity gate: the system does not globally search a generic category and manufacture a place.

### Zingerman's typo

Input: `Zingermans Delicatessen in Ann Arbor - want to go here for sandwiches sometime`

Result before user confirmation:

- status: `needs_review`
- top candidate: Zingerman's Deli
- pre-resolution match score: 0.8615
- pre-resolution gap: 0.0797

After the user chose the Deli:

- status: `resolved`
- method: `manual`
- original score/gap preserved

This validates typo-tolerant retrieval, ambiguity review, and truthful manual provenance.

### Detroit Institute of Arts

Input: `Detroit Institute of Arts in Detroit`

Result:

- status: `resolved`
- method: `auto`
- score: 1.0
- gap: 0.2259

Duplicate OSM representations no longer create false ambiguity.

### real TikTok screenshot: Stow Lake

The screenshot contained a small `STOW LAKE` logo on a pedal boat, a San Francisco location tag, and text about renting a pedal boat.

Extraction:

- name: `Stow Lake`
- city: `San Francisco`
- category: `boat rental`

Candidate retrieval returned current OSM entities headed by `Blue Heron Lake`, plus several road objects and the boathouse. The user confirmed `Blue Heron Lake`.

Result:

- status: `resolved`
- method: `manual`
- pre-resolution score: 0.6471
- pre-resolution gap: 0.0706

This exposed three follow-up requirements:

1. historical/alternate-name enrichment (`Stow Lake` → current `Blue Heron Lake`)
2. category semantics must distinguish the named entity type from an activity
3. non-venue road objects should not survive simply because the category string is unrecognized

## next work

- enrich OSM candidates with alternate/historical names using stable OSM IDs
- keep alias enrichment optional and non-fatal
- separate `category_hint` from `activity_hint`
- normalize common category synonyms through an explicit table
- filter non-venue OSM classes before ranking
- improve upload and review UX before the next screenshot batch

The original live JSON snapshot is retained outside the application database so this behavior remains auditable after fixes.
