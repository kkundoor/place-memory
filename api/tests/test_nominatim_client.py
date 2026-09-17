import httpx
import pytest

from app.clients.nominatim import NominatimClient
from app.models import PlaceHint


@pytest.mark.asyncio
async def test_nominatim_builds_query_sets_user_agent_and_normalizes_results():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen['query'] = request.url.params['q']
        seen['user_agent'] = request.headers['user-agent']
        return httpx.Response(200, json=[{
            'osm_type': 'node',
            'osm_id': 123,
            'lat': '40.963',
            'lon': '-72.184',
            'display_name': 'Example Bakery, East Hampton, New York',
            'namedetails': {'name': 'Example Bakery'},
            'category': 'shop',
            'type': 'bakery',
        }])

    client = NominatimClient(
        'https://nominatim.test',
        'place-memory-tests/1.0',
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
    )

    results = await client.search_places(PlaceHint(
        name='Example Bakery',
        city_hint='East Hampton',
        category_hint='bakery',
    ))

    assert seen['query'] == 'Example Bakery, East Hampton'
    assert seen['user_agent'] == 'place-memory-tests/1.0'
    assert results[0].place_id == 'osm:node:123'
    assert results[0].provider == 'nominatim'
    assert results[0].provider_place_id == 'node:123'
    assert results[0].name == 'Example Bakery'


@pytest.mark.asyncio
async def test_nominatim_caches_duplicate_queries():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[])

    client = NominatimClient(
        'https://nominatim.test',
        'place-memory-tests/1.0',
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
    )
    hint = PlaceHint(name='Same Place', city_hint='Detroit')

    await client.search_places(hint)
    await client.search_places(hint)

    assert calls == 1
