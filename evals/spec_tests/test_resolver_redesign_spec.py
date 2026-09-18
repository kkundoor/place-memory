import math

import pytest

from app import main
from app.clients.google_maps import RawPlace
from app.clients.photon import PhotonClient
from app.models import Memory, MemoryCreate, PlaceHint, ResolutionStatus
from app.services import resolver
from app.services.resolver import resolve_hint, score_candidate
from app.storage.sqlite import MemoryStore


def raw(
    place_id: str,
    name: str,
    address: str,
    primary_type: str,
    types: list[str],
    latitude: float = 42.28,
    longitude: float = -83.74,
) -> RawPlace:
    return RawPlace(
        place_id=place_id,
        name=name,
        formatted_address=address,
        latitude=latitude,
        longitude=longitude,
        primary_type=primary_type,
        types=types,
        provider='fixture',
        provider_place_id=place_id,
    )


class Search:
    def __init__(self, places):
        self.places = places
        self.calls = 0

    async def search_places(self, hint):
        self.calls += 1
        return self.places


@pytest.mark.asyncio
async def test_name_only_cannot_auto_resolve_without_independent_evidence():
    search = Search([
        raw('unique', 'Unique Place', '100 Main St, Somewhere, MI', 'restaurant', ['amenity', 'restaurant']),
    ])

    status, _, _ = await resolve_hint(PlaceHint(name='Unique Place'), search)

    assert status != ResolutionStatus.resolved


def test_correct_location_evidence_does_not_reduce_same_candidate_score():
    candidate = raw(
        'dia',
        'Detroit Institute of Arts',
        '5200 Woodward Avenue, Detroit, MI, 48202, United States',
        'museum',
        ['tourism', 'museum'],
    )

    name_only = score_candidate(PlaceHint(name='Detroit Institute of Arts'), candidate)
    with_city = score_candidate(
        PlaceHint(name='Detroit Institute of Arts', city_hint='Detroit'),
        candidate,
    )

    assert with_city.confidence >= name_only.confidence


def test_category_compatibility_is_an_explicit_finite_crosswalk():
    table = getattr(resolver, 'CATEGORY_COMPATIBILITY', None)

    assert isinstance(table, dict)
    assert table


@pytest.mark.asyncio
async def test_bakery_hint_rejects_boundary_place_road_and_station_entities():
    search = Search([
        raw('boundary', 'East Hampton North', 'East Hampton, New York', 'census', ['boundary', 'census']),
        raw('place', 'East Hampton', 'East Hampton, New York', 'town', ['place', 'town']),
        raw('road', "Carissa's Bakery Road", 'East Hampton, New York', 'residential', ['highway', 'residential']),
        raw('station', 'East Hampton', 'East Hampton, New York', 'station', ['railway', 'station']),
    ])

    status, selected, candidates = await resolve_hint(
        PlaceHint(name="Carissa's Bakery", city_hint='East Hampton', category_hint='bakery'),
        search,
    )

    assert status == ResolutionStatus.unresolved
    assert selected is None
    assert candidates == []


@pytest.mark.asyncio
async def test_dia_duplicate_provider_records_do_not_create_false_ambiguity():
    places = [
        raw(
            'photon:N:10905214429',
            'Detroit Institute of Arts',
            'John R Street, Detroit, Michigan, 48203, United States',
            'arts_centre',
            ['amenity', 'arts_centre'],
            42.3595402,
            -83.0641933,
        ),
        raw(
            'photon:R:1553447',
            'Detroit Institute of Arts',
            '5200 Woodward Avenue, Detroit, MI, 48202, United States',
            'museum',
            ['tourism', 'museum'],
            42.3595055,
            -83.0645225,
        ),
        raw(
            'martial',
            'Institute of Martial Arts',
            '16849 West Warren Avenue, Detroit, MI, 48239, United States',
            'dojo',
            ['amenity', 'dojo'],
            42.3432216,
            -83.2108339,
        ),
    ]

    status, selected, ranked = await resolve_hint(
        PlaceHint(name='Detroit Institute of Arts', city_hint='Detroit'),
        Search(places),
    )

    assert status == ResolutionStatus.resolved
    assert selected is not None
    assert selected.name == 'Detroit Institute of Arts'
    assert len([candidate for candidate in ranked if candidate.name == 'Detroit Institute of Arts']) == 1


@pytest.mark.asyncio
async def test_dedup_guard_keeps_two_nearby_same_name_branches_distinct():
    places = [
        raw(
            'sb-1',
            'Starbucks',
            '100 Main Street, Ann Arbor, MI',
            'cafe',
            ['amenity', 'cafe'],
            42.2800,
            -83.7400,
        ),
        raw(
            'sb-2',
            'Starbucks',
            '120 Main Street, Ann Arbor, MI',
            'cafe',
            ['amenity', 'cafe'],
            42.2802,
            -83.7401,
        ),
    ]

    status, selected, ranked = await resolve_hint(
        PlaceHint(name='Starbucks', city_hint='Ann Arbor'),
        Search(places),
    )

    assert status == ResolutionStatus.needs_review
    assert len(ranked) == 2


def test_memory_has_first_class_resolution_provenance_fields():
    fields = Memory.model_fields

    assert 'resolution_method' in fields
    assert 'pre_resolution_confidence' in fields
    assert 'pre_resolution_gap' in fields


@pytest.mark.asyncio
async def test_unknown_identity_can_be_represented_and_abstains_before_search():
    hint = PlaceHint(
        name=None,
        category_hint='coffee shop',
        evidence='my friend sent me this coffee shop and said the croissants were amazing',
    )
    search = Search([
        raw('road', 'Coffee Shop Road', 'Ripley, Tennessee', 'unclassified', ['highway', 'unclassified']),
    ])

    status, selected, ranked = await resolve_hint(hint, search)

    assert status == ResolutionStatus.unresolved
    assert selected is None
    assert ranked == []
    assert search.calls == 0


@pytest.mark.asyncio
async def test_conflicting_city_prevents_auto_resolution():
    search = Search([
        raw(
            'wrong-city',
            'Union Coffee',
            '100 Main Street, Chicago, IL',
            'cafe',
            ['amenity', 'cafe'],
        ),
    ])

    status, _, _ = await resolve_hint(
        PlaceHint(name='Union Coffee', city_hint='Detroit', category_hint='cafe'),
        search,
    )

    assert status != ResolutionStatus.resolved


@pytest.mark.asyncio
async def test_realistic_two_signal_unique_place_can_reach_auto_resolution():
    search = Search([
        raw(
            'dia',
            'Detroit Institute of Arts',
            '5200 Woodward Avenue, Detroit, MI, 48202, United States',
            'museum',
            ['tourism', 'museum'],
            42.3595055,
            -83.0645225,
        ),
    ])

    status, selected, _ = await resolve_hint(
        PlaceHint(name='Detroit Institute of Arts', city_hint='Detroit'),
        search,
    )

    assert status == ResolutionStatus.resolved
    assert selected is not None


def test_unicode_survives_photon_normalization():
    feature = {
        'geometry': {'coordinates': [-83.7452712, 42.28455]},
        'properties': {
            'name': "Zingerman's Next Door Café",
            'city': 'Ann Arbor',
            'state': 'Michigan',
            'country': 'United States',
            'osm_key': 'amenity',
            'osm_value': 'cafe',
            'osm_type': 'N',
            'osm_id': 12552300477,
        },
    }

    parsed = PhotonClient._parse(feature)

    assert parsed is not None
    assert parsed.name == "Zingerman's Next Door Café"


def test_unicode_survives_sqlite_round_trip(tmp_path):
    store = MemoryStore(str(tmp_path / 'unicode.db'))
    memory = store.create(MemoryCreate(
        source_text="saved Zingerman's Next Door Café in Quindío",
        hint=PlaceHint(name="Zingerman's Next Door Café", city_hint='Quindío'),
    ))

    loaded = store.get(memory.id)

    assert loaded is not None
    assert loaded.source_text == "saved Zingerman's Next Door Café in Quindío"
    assert loaded.hint is not None
    assert loaded.hint.name == "Zingerman's Next Door Café"
    assert loaded.hint.city_hint == 'Quindío'


def test_review_api_exposes_explicit_none_of_these_path():
    paths = {route.path for route in main.app.routes}

    assert '/api/memories/{memory_id}/reject' in paths
