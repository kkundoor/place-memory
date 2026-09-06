# field test - 2026-09-07

## goal

Test whether saved-place memory is useful in a real day out, not whether the UI looks finished.

## minimum working path

1. add a saved item
2. extract or enter a place hint
3. resolve it to a canonical place
4. save the evidence and confidence
5. retrieve it with a natural query
6. check whether it is feasible from the current location and time
7. act on at least one result

## test set

Use 8-12 real saves from the trip if possible:

- 3 obvious place screenshots / links
- 3 partially ambiguous saves
- 2 category or vibe-heavy saves where the place name is not the main text
- 1-2 intentionally hard / unresolved cases

Do not curate only easy examples.

## questions to try

- what did I save near me?
- what from my saves can I do in the next 90 minutes?
- show me something I saved for coffee or lunch that is actually doable now
- what did I save around this part of the Hamptons?
- what is not feasible right now, and why?

## record for every result

- expected place
- resolved place
- confidence
- whether the result should have been surfaced
- open-hours correctness
- predicted travel time
- actual travel time if visited
- useful / not useful
- failure reason

## success bar

The first field test is a pass if:

- obvious saves resolve correctly
- ambiguous saves fail safely instead of confidently resolving to the wrong place
- natural retrieval returns relevant saved items
- feasibility explanations use live tool data or clearly say when data is unavailable
- at least one recommendation is useful enough to act on

## failure taxonomy

- extraction miss
- wrong place candidate
- confidence gate too loose
- confidence gate too strict
- retrieval miss
- hours unavailable / stale
- route failure
- bad feasibility policy
- UI friction

The failures become the next commits. Do not hide them.
