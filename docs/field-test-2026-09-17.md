# field test — 2026-09-17

This file records the live behaviors that changed the resolver design.

The live JSON captures were taken at different commits and from reseeded local databases. The checked-in field corpus is a set of repeatable scenario fixtures distilled from those runs; it is not one continuously-growing database export.

## before the resolver redesign

Live testing surfaced several failures that the original clean fixture set did not catch:

- generic place descriptions could trigger global candidate search
- missing evidence could still contribute confidence
- correct city evidence could lower a score
- incompatible entity classes could survive into review
- duplicate OSM records could create false ambiguity
- manual confirmation was not represented separately from automatic resolution

Those findings became resolver invariants before the implementation was changed.

See [`resolver-redesign-spec.md`](resolver-redesign-spec.md).

## post-redesign checks

### generic coffee-shop note

A note describing "this coffee shop" without an actual place identity now produces:

- `status: unresolved`
- `resolution_method: abstained`
- zero candidates

The system does not invent an identity from a generic category.

### Zingerman's typo

Input:

```text
Zingermans Delicatessen in Ann Arbor - want to go here for sandwiches sometime
```

The correct Deli candidate ranked first, but the gap to another Zingerman's location was below the automatic-resolution bar.

Result before confirmation:

- `status: needs_review`
- top candidate: `Zingerman's Deli`
- score: `0.8615`
- gap: `0.0797`

After the user selected the Deli:

- `status: resolved`
- `resolution_method: manual`
- the original score and gap remained unchanged

### Detroit Institute of Arts

Input:

```text
Detroit Institute of Arts in Detroit
```

Duplicate OSM representations were collapsed before ambiguity was measured.

Result:

- `status: resolved`
- `resolution_method: auto`
- score: `1.0`
- gap: `0.2259`

## Stow Lake screenshot: before alias support

The screenshot showed:

- a small `STOW LAKE` logo on a pedal boat
- a San Francisco location tag
- text about renting a pedal boat

At commit `67655d8`, extraction identified `Stow Lake`, but the resolver only had ordinary string similarity against the current `Blue Heron Lake` name.

The result was:

- correct current place retrieved
- score: `0.6471`
- gap: `0.0706`
- `resolution_method: manual` after user confirmation
- road objects also appeared as candidates

This was not an alias-resolution success. It was the failure that motivated the alias and entity-semantics changes.

## Stow Lake screenshot: after alias support

The same scenario was rerun at commit:

```text
3a90f803ea6ecfff54b9da33a0ead94835ed880e
```

The live capture showed:

```text
hint.name: Stow Lake
hint.city_hint: San Francisco
hint.category_hint: lake
hint.activity_hint: pedal boat rental

place.name: Blue Heron Lake
resolution_status: resolved
resolution_method: auto
pre_resolution_confidence: 1.0
pre_resolution_gap: 1.0

name=1.00
name_source=alias:Stow Lake
location=1.00
category=1.00
entity_family=lake
```

This is the first live capture that proves the historical-name mechanism supplied the winning name evidence for this screenshot.

That same capture exposed one follow-up bug: broad `name:*` parsing also pulled in etymology metadata that was not actually a place alias. The parser was then narrowed to explicit alias/history fields plus language-qualified `name:<language>` keys, with a regression test.

## current field scenarios

The repeatable field-regression corpus currently contains six distinct scenario types:

1. Zingerman's typo + ambiguity
2. Starbucks branch ambiguity
3. Carissa's provider miss
4. Detroit Institute of Arts duplicate records
5. generic coffee-shop abstention
6. Stow Lake historical-name resolution

These are scenario fixtures derived from versioned runs, not six rows from one live database.
