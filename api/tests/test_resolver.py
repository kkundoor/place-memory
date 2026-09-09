import pytest

from app.clients.google_maps import RawPlace
from app.models import PlaceHint, ResolutionStatus
from app.services.resolver import resolve_hint, score_candidate


def test_exact_name_and_city_scores_high():
    hint = PlaceHint(name='Carissa’s Bakery', city_hint='East Hampton', category_hint='bakery')
    place = RawPlace(
        place_id='p1',
        name='Carissa’s Bakery',
        formatted_address='East Hampton, NY',
        latitude=40.96,
        longitude=-72.18,
        primary_type='bakery',
        types=['bakery', 'food'],
    )

    scored = score_candidate(hint, place)

    assert scored.confidence > 0.85


def test_wrong_name_does_not_get_false_confidence():
    hint = PlaceHint(name='Carissa’s Bakery', city_hint='East Hampton', category_hint='bakery')
    place = RawPlace(
        place_id='p2',
        name='East Hampton Grill',
        formatted_address='East Hampton, NY',
        latitude=40.96,
        longitude=-72.18,
        primary_type='restaurant',
        types=['restaurant', 'food'],
    )

    scored = score_candidate(hint, place)

    assert scored.confidence < 0.76


class FakeMaps:
    def __init__(self, places):
        self.places = places

    async def search_places(self, hint):
        return self.places


@pytest.mark.asyncio
async def test_resolver_accepts_clear_winner():
    hint = PlaceHint(name='Carissa’s Bakery', city_hint='East Hampton', category_hint='bakery')
    places = [
        RawPlace(
            place_id='p1',
            name='Carissa’s Bakery',
            formatted_address='East Hampton, NY',
            latitude=40.96,
            longitude=-72.18,
            primary_type='bakery',
            types=['bakery', 'food'],
        ),
        RawPlace(
            place_id='p2',
            name='East Hampton Grill',
            formatted_address='East Hampton, NY',
            latitude=40.96,
            longitude=-72.18,
            primary_type='restaurant',
            types=['restaurant', 'food'],
        ),
    ]

    status, selected, ranked = await resolve_hint(hint, FakeMaps(places))

    assert status == ResolutionStatus.resolved
    assert selected.place_id == 'p1'
    assert ranked[0].place_id == 'p1'


@pytest.mark.asyncio
async def test_resolver_sends_close_match_to_review():
    hint = PlaceHint(name='The Point', city_hint='Southampton')
    places = [
        RawPlace(
            place_id='p1',
            name='The Point Bar',
            formatted_address='Southampton, NY',
            latitude=40.89,
            longitude=-72.39,
            primary_type='bar',
            types=['bar'],
        ),
        RawPlace(
            place_id='p2',
            name='The Point Cafe',
            formatted_address='Southampton, NY',
            latitude=40.89,
            longitude=-72.39,
            primary_type='cafe',
            types=['cafe'],
        ),
    ]

    status, selected, ranked = await resolve_hint(hint, FakeMaps(places))

    assert status == ResolutionStatus.needs_review
    assert selected is not None
    assert len(ranked) == 2


@pytest.mark.asyncio
async def test_resolver_stays_unresolved_without_candidates():
    status, selected, ranked = await resolve_hint(
        PlaceHint(name='missing place'),
        FakeMaps([]),
    )

    assert status == ResolutionStatus.unresolved
    assert selected is None
    assert ranked == []
