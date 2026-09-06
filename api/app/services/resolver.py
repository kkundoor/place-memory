from rapidfuzz.fuzz import ratio

from app.clients.google_maps import GoogleMapsClient, RawPlace
from app.models import PlaceCandidate, PlaceHint, ResolutionStatus


RESOLVE_THRESHOLD = 0.76
AMBIGUITY_GAP = 0.10


def _norm(value: str | None) -> str:
    return ' '.join((value or '').lower().split())


def score_candidate(hint: PlaceHint, place: RawPlace) -> PlaceCandidate:
    name_score = ratio(_norm(hint.name), _norm(place.name)) / 100

    location_text = _norm(' '.join(filter(None, [place.formatted_address])))
    location_hints = ' '.join(filter(None, [hint.city_hint, hint.address_hint]))
    location_score = ratio(_norm(location_hints), location_text) / 100 if location_hints else 0.5

    candidate_types = {_norm(x) for x in place.types}
    if place.primary_type:
        candidate_types.add(_norm(place.primary_type))
    category = _norm(hint.category_hint)
    category_score = 0.5 if not category else max(
        [ratio(category, item) / 100 for item in candidate_types] or [0.0]
    )

    confidence = 0.60 * name_score + 0.25 * location_score + 0.15 * category_score
    reasons = [
        f'name={name_score:.2f}',
        f'location={location_score:.2f}',
        f'category={category_score:.2f}',
    ]

    return PlaceCandidate(
        place_id=place.place_id,
        name=place.name,
        formatted_address=place.formatted_address,
        latitude=place.latitude,
        longitude=place.longitude,
        primary_type=place.primary_type,
        types=place.types,
        confidence=round(confidence, 4),
        confidence_reasons=reasons,
    )


async def resolve_hint(
    hint: PlaceHint,
    client: GoogleMapsClient,
) -> tuple[ResolutionStatus, PlaceCandidate | None, list[PlaceCandidate]]:
    raw = await client.search_places(hint)
    ranked = sorted(
        [score_candidate(hint, item) for item in raw],
        key=lambda item: item.confidence,
        reverse=True,
    )
    if not ranked:
        return ResolutionStatus.unresolved, None, []

    top = ranked[0]
    gap = top.confidence - ranked[1].confidence if len(ranked) > 1 else 1.0
    if top.confidence < RESOLVE_THRESHOLD or gap < AMBIGUITY_GAP:
        return ResolutionStatus.needs_review, top, ranked
    return ResolutionStatus.resolved, top, ranked
