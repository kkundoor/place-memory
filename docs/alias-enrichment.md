# alias enrichment

## problem

Search providers may return a current canonical name while the saved artifact contains a valid historical or alternate name.

For example:

```text
artifact: Stow Lake
current provider name: Blue Heron Lake
```

Pure edit distance treats those as a weak name match even though they refer to the same place.

## current approach

Photon remains the candidate-search provider for the no-key path.

For returned OSM objects, a small enrichment adapter uses the stable OSM object ID to request name metadata from Nominatim `/lookup`. The resolver then compares the artifact name against:

- the canonical name
- explicit historical / alternate names
- language-qualified place names

The alias metadata is optional. If lookup fails, the Photon candidates still continue through the resolver unchanged.

## accepted alias metadata

The parser accepts explicit name-history fields such as:

- `old_name`
- `alt_name`
- `loc_name`
- `short_name`
- `official_name`

It also accepts language-qualified keys such as `name:es`.

It does **not** treat arbitrary `name:*` metadata as an alias. In particular, etymology metadata such as `name:etymology` or `name:etymology:wikidata` is not identity evidence.

## safety

An alias match strengthens the name signal; it does not bypass the rest of the policy.

Automatic resolution still requires independent evidence and enough separation from other candidates.

There is also a controlled alias-collision test: if two different candidates share the same alias and otherwise look equally plausible, both receive the strong alias name signal and the normal ambiguity rule keeps the result in review.
