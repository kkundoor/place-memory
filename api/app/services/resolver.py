import math
import re
import unicodedata
from typing import Protocol

from rapidfuzz.fuzz import ratio

from app.clients.google_maps import RawPlace
from app.models import PlaceCandidate, PlaceHint, ResolutionMethod, ResolutionStatus


RESOLVE_THRESHOLD = 0.76
AMBIGUITY_GAP = 0.10
AUTO_NAME_FLOOR = 0.85
AUTO_SIGNAL_FLOOR = 0.80
DEDUP_DISTANCE_METERS = 50.0

CATEGORY_COMPATIBILITY: dict[str, set[str]] = {
    'bakery': {'bakery'},
    'cafe': {'cafe'},
    'coffee shop': {'cafe'},
    'coffee_shop': {'cafe'},
    'delicatessen': {'deli', 'restaurant'},
    'deli': {'deli', 'restaurant'},
    'restaurant': {'restaurant', 'deli'},
    'museum': {'museum'},
    'arts centre': {'museum'},
    'arts_centre': {'museum'},
    'stadium': {'stadium'},
    'bar': {'bar', 'restaurant'},
    'pub': {'bar', 'restaurant'},
    'grocery': {'grocery'},
    'grocery store': {'grocery'},
    'supermarket': {'grocery'},
}

GENERIC_IDENTITY_NAMES = {
    'bakery', 'cafe', 'coffee shop', 'coffee_shop', 'deli', 'delicatessen',
    'restaurant', 'museum', 'bar', 'pub', 'stadium', 'grocery store',
}

NON_VENUE_ROOT_TAGS = {'boundary', 'place', 'highway', 'railway', 'landuse'}


class PlaceSearchClient(Protocol):
    async def search_places(self, hint: PlaceHint) -> list[RawPlace]: ...


def _norm(value: str | None) -> str:
    text = unicodedata.normalize('NFKD', value or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return ' '.join(re.findall(r'[a-z0-9]+', text))


def _name_score(hint: PlaceHint, place: RawPlace | PlaceCandidate) -> float | None:
    if not _norm(hint.name):
        return None
    return ratio(_norm(hint.name), _norm(place.name)) / 100


def _location_score(hint: PlaceHint, place: RawPlace | PlaceCandidate) -> float | None:
    address = _norm(place.formatted_address)
    target = _norm(hint.address_hint or hint.city_hint)
    if not target:
        return None
    if not address:
        return 0.0
    address_tokens = set(address.split())
    return 1.0 if all(token in address_tokens for token in target.split()) else 0.0


def _entity_family(place: RawPlace | PlaceCandidate) -> str:
    tags = {_norm(item) for item in place.types if _norm(item)}
    primary = _norm(place.primary_type)
    if primary:
        tags.add(primary)
    if tags & NON_VENUE_ROOT_TAGS:
        return 'non_venue'
    if 'bakery' in tags:
        return 'bakery'
    if tags & {'cafe', 'coffee shop', 'coffee_shop'}:
        return 'cafe'
    if tags & {'deli', 'delicatessen'}:
        return 'deli'
    if tags & {'restaurant', 'fast food', 'fast_food', 'food court', 'food_court'}:
        return 'restaurant'
    if tags & {'museum', 'arts centre', 'arts_centre', 'gallery'}:
        return 'museum'
    if 'stadium' in tags:
        return 'stadium'
    if tags & {'bar', 'pub', 'nightclub'}:
        return 'bar'
    if tags & {'supermarket', 'grocery', 'grocery store', 'convenience'}:
        return 'grocery'
    if 'dairy' in tags:
        return 'dairy'
    if 'office' in tags:
        return 'office'
    if tags & {'store', 'retail'}:
        return 'retail'
    return 'unknown'


def _category_score(hint: PlaceHint, place: RawPlace | PlaceCandidate) -> float | None:
    category = _norm(hint.category_hint)
    if not category:
        return None
    allowed = CATEGORY_COMPATIBILITY.get(category)
    if allowed is None:
        return None
    family = _entity_family(place)
    if family == 'unknown':
        return None
    return 1.0 if family in allowed else 0.0


def _category_eligible(hint: PlaceHint, place: RawPlace) -> bool:
    category = _norm(hint.category_hint)
    allowed = CATEGORY_COMPATIBILITY.get(category)
    if allowed is None:
        return True
    family = _entity_family(place)
    if family == 'non_venue':
        return False
    if family == 'unknown':
        return True
    return family in allowed


def _is_generic_identity(hint: PlaceHint) -> bool:
    name = _norm(hint.name)
    if not name:
        return True
    category = _norm(hint.category_hint)
    return (bool(category) and name == category) or name in GENERIC_IDENTITY_NAMES


def _haversine_meters(a: RawPlace, b: RawPlace) -> float:
    radius = 6_371_000.0
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat = math.radians(b.latitude - a.latitude)
    dlon = math.radians(b.longitude - a.longitude)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def _house_number(place: RawPlace) -> str | None:
    match = re.match(r'\s*(\d+[a-zA-Z]?)\b', place.formatted_address or '')
    return match.group(1).lower() if match else None


def _osm_geometry(place: RawPlace) -> str | None:
    for part in (place.provider_place_id or place.place_id).split(':'):
        if part.upper() in {'N', 'W', 'R'}:
            return part.upper()
    return None


def _same_real_place(a: RawPlace, b: RawPlace) -> bool:
    if _norm(a.name) != _norm(b.name):
        return False
    ga, gb = _osm_geometry(a), _osm_geometry(b)
    if not ga or not gb or ga == gb:
        return False
    na, nb = _house_number(a), _house_number(b)
    if na and nb and na != nb:
        return False
    fa, fb = _entity_family(a), _entity_family(b)
    if fa != fb and 'unknown' not in {fa, fb} and {fa, fb} != {'museum'}:
        return False
    return _haversine_meters(a, b) <= DEDUP_DISTANCE_METERS


def _dedupe_places(places: list[RawPlace]) -> list[RawPlace]:
    kept: list[RawPlace] = []
    for place in places:
        if any(_same_real_place(existing, place) for existing in kept):
            continue
        kept.append(place)
    return kept


def score_candidate(hint: PlaceHint, place: RawPlace) -> PlaceCandidate:
    name_score = _name_score(hint, place)
    location_score = _location_score(hint, place)
    category_score = _category_score(hint, place)
    weighted = [(0.60, name_score), (0.25, location_score), (0.15, category_score)]
    present = [(w, s) for w, s in weighted if s is not None]
    confidence = (
        sum(w * s for w, s in present) / sum(w for w, _ in present)
        if present else 0.0
    )
    reasons = [
        f'name={name_score:.2f}' if name_score is not None else 'name=missing',
        f'location={location_score:.2f}' if location_score is not None else 'location=missing',
        f'category={category_score:.2f}' if category_score is not None else 'category=missing',
        f'entity_family={_entity_family(place)}',
    ]
    return PlaceCandidate(
        place_id=place.place_id,
        provider=place.provider,
        provider_place_id=place.provider_place_id or place.place_id,
        name=place.name,
        formatted_address=place.formatted_address,
        latitude=place.latitude,
        longitude=place.longitude,
        primary_type=place.primary_type,
        types=place.types,
        confidence=round(confidence, 4),
        confidence_reasons=reasons,
    )


def _auto_eligible(hint: PlaceHint, candidate: PlaceCandidate) -> bool:
    name_score = _name_score(hint, candidate)
    location_score = _location_score(hint, candidate)
    category_score = _category_score(hint, candidate)
    if name_score is None or name_score < AUTO_NAME_FLOOR:
        return False
    if (hint.city_hint or hint.address_hint) and location_score == 0.0:
        return False
    if hint.category_hint and category_score == 0.0:
        return False
    strong = int(name_score >= AUTO_NAME_FLOOR)
    strong += int(location_score is not None and location_score >= AUTO_SIGNAL_FLOOR)
    strong += int(category_score is not None and category_score >= AUTO_SIGNAL_FLOOR)
    return strong >= 2


def resolution_metrics(ranked: list[PlaceCandidate]) -> tuple[float | None, float | None]:
    if not ranked:
        return None, None
    top = ranked[0].confidence
    gap = top - ranked[1].confidence if len(ranked) > 1 else 1.0
    return top, round(gap, 4)


def decide_resolution(
    ranked: list[PlaceCandidate],
    hint: PlaceHint | None = None,
) -> tuple[ResolutionStatus, PlaceCandidate | None]:
    if not ranked:
        return ResolutionStatus.unresolved, None
    top = ranked[0]
    _, gap = resolution_metrics(ranked)
    if (
        top.confidence < RESOLVE_THRESHOLD
        or (gap is not None and gap < AMBIGUITY_GAP)
        or (hint is not None and not _auto_eligible(hint, top))
    ):
        return ResolutionStatus.needs_review, top
    return ResolutionStatus.resolved, top


def explain_resolution(
    status: ResolutionStatus,
    candidates: list[PlaceCandidate],
    resolution_method: ResolutionMethod | None = None,
    pre_resolution_confidence: float | None = None,
    pre_resolution_gap: float | None = None,
) -> dict:
    top_confidence, top_gap = resolution_metrics(candidates)
    if pre_resolution_confidence is not None:
        top_confidence = pre_resolution_confidence
    if pre_resolution_gap is not None:
        top_gap = pre_resolution_gap
    if resolution_method == ResolutionMethod.manual:
        decision = 'resolved by user confirmation after review'
    elif resolution_method == ResolutionMethod.auto:
        decision = 'auto-resolved: evidence sufficiency, confidence, and separation passed policy'
    elif resolution_method == ResolutionMethod.abstained:
        decision = 'abstained: available evidence did not justify a canonical place'
    elif status == ResolutionStatus.needs_review:
        decision = 'review required: candidates exist but automatic-resolution policy did not pass'
    elif status == ResolutionStatus.unresolved:
        decision = 'unresolved: no eligible candidate or identity anchor'
    else:
        decision = 'resolved'
    return {
        'status': status.value,
        'resolution_method': resolution_method.value if resolution_method else None,
        'policy': {
            'resolve_threshold': RESOLVE_THRESHOLD,
            'ambiguity_gap': AMBIGUITY_GAP,
            'auto_name_floor': AUTO_NAME_FLOOR,
            'minimum_independent_signals': 2,
        },
        'top_confidence': top_confidence,
        'top_gap': top_gap,
        'decision': decision,
        'candidates': [candidate.model_dump() for candidate in candidates],
    }


async def resolve_hint(
    hint: PlaceHint,
    client: PlaceSearchClient,
) -> tuple[ResolutionStatus, PlaceCandidate | None, list[PlaceCandidate]]:
    if _is_generic_identity(hint):
        return ResolutionStatus.unresolved, None, []
    raw = await client.search_places(hint)
    eligible = [place for place in raw if _category_eligible(hint, place)]
    deduped = _dedupe_places(eligible)
    ranked = sorted(
        [score_candidate(hint, item) for item in deduped],
        key=lambda item: item.confidence,
        reverse=True,
    )
    status, selected = decide_resolution(ranked, hint)
    return status, selected, ranked
