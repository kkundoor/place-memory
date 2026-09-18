import httpx
import pytest

from app.clients.enriched import AliasEnrichedPlaceSearchClient
from app.clients.google_maps import RawPlace
from app.clients.nominatim import NominatimClient
from app.models import PlaceHint, ResolutionStatus
from app.services.resolver import resolve_hint


def place(
    place_id: str,
    name: str,
    address: str,
    primary_type: str,
    types: list[str],
    aliases: list[str] | None = None,
    latitude: float = 37.769,
    longitude: float = -122.473,
) -> RawPlace:
    return RawPlace(
        place_id=place_id,
        name=name,
        aliases=aliases or [],
        formatted_address=address,
        latitude=latitude,
        longitude=longitude,
        primary_type=primary_type,
        types=types,
        provider='photon',
        provider_place_id=place_id.removeprefix('photon:'),
    )


@pytest.mark.asyncio
async def test_nominatim_lookup_extracts_historical_aliases_and_caches():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        assert request.url.path == '/lookup'
        assert request.url.params['osm_ids'] == 'R12908'
        assert request.url.params['namedetails'] == '1'
        return httpx.Response(200, json=[{
            'osm_type': 'relation',
            'osm_id': 12908,
            'namedetails': {
                'name': 'Blue Heron Lake',
                'old_name': 'Stow Lake',
                'name:es': 'Lago Blue Heron',
                'old_name:etymology': 'William W. Stow',
                'old_name:etymology:wikidata': 'Q116225246',
                'old_name:etymology:wikipedia': 'en:William W. Stow',
                'name:etymology': 'William W. Stow',
                'name:etymology:wikidata': 'Q116225246',
                'name:etymology:wikipedia': 'en:William W. Stow',
                'brand': 'not an alias signal',
            },
        }])

    client = NominatimClient(
        'https://nominatim.test',
        'place-memory-tests/1.0',
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
    )
    candidate = place(
        'photon:R:12908',
        'Blue Heron Lake',
        'San Francisco, California, United States',
        'lake',
        ['water', 'lake'],
    )

    first = await client.lookup_aliases([candidate])
    second = await client.lookup_aliases([candidate])

    assert first[candidate.place_id] == ['Stow Lake', 'Lago Blue Heron']
    assert second == first
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_alias_enrichment_is_nonfatal_when_metadata_lookup_fails():
    candidate = place(
        'photon:R:12908',
        'Blue Heron Lake',
        'San Francisco, California, United States',
        'lake',
        ['water', 'lake'],
    )

    class Search:
        enabled = True

        async def search_places(self, hint):
            return [candidate]

    class Aliases:
        enabled = True

        async def lookup_aliases(self, places):
            raise httpx.ConnectError('metadata offline')

    results = await AliasEnrichedPlaceSearchClient(Search(), Aliases()).search_places(
        PlaceHint(name='Stow Lake', city_hint='San Francisco')
    )

    assert results == [candidate]


@pytest.mark.asyncio
async def test_historical_alias_can_auto_resolve_current_canonical_place():
    candidate = place(
        'photon:R:12908',
        'Blue Heron Lake',
        'San Francisco, California, United States',
        'lake',
        ['water', 'lake'],
        aliases=['Stow Lake'],
    )

    class Search:
        async def search_places(self, hint):
            return [candidate]

    status, selected, ranked = await resolve_hint(
        PlaceHint(
            name='Stow Lake',
            city_hint='San Francisco',
            category_hint='lake',
            activity_hint='boat rental',
        ),
        Search(),
    )

    assert status == ResolutionStatus.resolved
    assert selected is not None
    assert selected.name == 'Blue Heron Lake'
    assert selected.aliases == ['Stow Lake']
    assert ranked[0].confidence == 1.0
    assert 'name_source=alias:Stow Lake' in ranked[0].confidence_reasons


@pytest.mark.asyncio
async def test_alias_collision_stays_in_review():
    candidates = [
        place(
            'photon:N:1',
            'North Harbor Cafe',
            '10 Main Street, Detroit, Michigan, United States',
            'cafe',
            ['amenity', 'cafe'],
            aliases=['Old Mill'],
            latitude=42.330,
            longitude=-83.040,
        ),
        place(
            'photon:N:2',
            'South Harbor Cafe',
            '20 Main Street, Detroit, Michigan, United States',
            'cafe',
            ['amenity', 'cafe'],
            aliases=['Old Mill'],
            latitude=42.331,
            longitude=-83.041,
        ),
    ]

    class Search:
        async def search_places(self, hint):
            return candidates

    status, selected, ranked = await resolve_hint(
        PlaceHint(name='Old Mill', city_hint='Detroit', category_hint='cafe'),
        Search(),
    )

    assert status == ResolutionStatus.needs_review
    assert selected is not None
    assert len(ranked) == 2
    assert ranked[0].confidence == 1.0
    assert ranked[1].confidence == 1.0
    assert 'name_source=alias:Old Mill' in ranked[0].confidence_reasons
    assert 'name_source=alias:Old Mill' in ranked[1].confidence_reasons


@pytest.mark.asyncio
async def test_nonvenue_entities_are_filtered_even_for_unrecognized_category():
    candidates = [
        place(
            'photon:W:1',
            'Blue Heron Lake Drive',
            'San Francisco, California, United States',
            'pedestrian',
            ['highway', 'pedestrian'],
        ),
    ]

    class Search:
        async def search_places(self, hint):
            return candidates

    status, selected, ranked = await resolve_hint(
        PlaceHint(name='Some Place', city_hint='San Francisco', category_hint='unexpected activity'),
        Search(),
    )

    assert status == ResolutionStatus.unresolved
    assert selected is None
    assert ranked == []


def test_category_synonyms_map_to_canonical_entity_families():
    museum = place(
        'photon:R:1553447',
        'Detroit Institute of Arts',
        'Detroit, Michigan, United States',
        'museum',
        ['tourism', 'museum'],
    )

    from app.services.resolver import score_candidate

    scored = score_candidate(
        PlaceHint(
            name='Detroit Institute of Arts',
            city_hint='Detroit',
            category_hint='art museum',
        ),
        museum,
    )

    assert 'category=1.00' in scored.confidence_reasons
