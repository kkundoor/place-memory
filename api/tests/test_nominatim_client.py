import httpx
import pytest

from app.clients.nominatim import NominatimClient
from app.models import PlaceHint


@pytest.mark.asyncio
async def test_search_places_identifies_app_and_parses_candidates():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen['url'] = request.url
        seen['user_agent'] = request.headers['user-agent']
        return httpx.Response(200, json=[
            {
                'place_id': 123,
                'osm_type': 'node',
                'osm_id': 456,
                'lat': '40.972',
                'lon': '-72.181',
                'display_name': 'Carissa’s Bakery, East Hampton, New York, USA',
                'category': 'shop',
                'type': 'bakery',
                'namedetails': {'name': 'Carissa’s Bakery'},
                'address': {
                    'shop': 'Carissa’s Bakery',
                    'town': 'East Hampton',
                },
            }
        ])

    client = NominatimClient(
        'https://nominatim.example',
        'place-memory-test/0.1',
        min_interval_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    places = await client.search_places(PlaceHint(
        name='Carissa’s Bakery',
        city_hint='East Hampton',
        category_hint='bakery',
    ))

    assert seen['url'].params['q'] == 'Carissa’s Bakery, East Hampton'
    assert seen['url'].params['limit'] == '5'
    assert seen['user_agent'] == 'place-memory-test/0.1'
    assert places[0].place_id == 'osm:node:456'
    assert places[0].name == 'Carissa’s Bakery'
    assert places[0].primary_type == 'bakery'
    assert places[0].types == ['shop', 'bakery']
    assert places[0].latitude == 40.972


@pytest.mark.asyncio
async def test_search_places_caches_duplicate_query():
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json=[])

    client = NominatimClient(
        'https://nominatim.example',
        'place-memory-test/0.1',
        min_interval_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    hint = PlaceHint(name='Saved Place')

    await client.search_places(hint)
    await client.search_places(hint)

    assert request_count == 1