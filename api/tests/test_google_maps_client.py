import json

import httpx
import pytest

from app.clients.google_maps import GoogleMapsClient
from app.models import Origin, PlaceHint


@pytest.mark.asyncio
async def test_search_places_builds_grounded_query_and_parses_candidates():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen['url'] = str(request.url)
        seen['headers'] = request.headers
        seen['body'] = json.loads(request.content)
        return httpx.Response(200, json={
            'places': [
                {
                    'id': 'place-1',
                    'displayName': {'text': 'Carissa’s Bakery'},
                    'formattedAddress': '221 Pantigo Rd, East Hampton, NY',
                    'location': {'latitude': 40.97, 'longitude': -72.17},
                    'primaryType': 'bakery',
                    'types': ['bakery', 'food'],
                }
            ]
        })

    client = GoogleMapsClient('secret-key', transport=httpx.MockTransport(handler))
    places = await client.search_places(PlaceHint(
        name='Carissa’s Bakery',
        city_hint='East Hampton',
        category_hint='bakery',
    ))

    assert seen['url'] == 'https://places.googleapis.com/v1/places:searchText'
    assert seen['headers']['x-goog-api-key'] == 'secret-key'
    assert seen['body'] == {
        'textQuery': 'Carissa’s Bakery, East Hampton',
        'maxResultCount': 5,
    }
    assert places[0].place_id == 'place-1'
    assert places[0].primary_type == 'bakery'
    assert places[0].latitude == 40.97


@pytest.mark.asyncio
async def test_status_parses_live_open_flag():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/v1/places/place-1'
        assert request.headers['x-goog-fieldmask'] == 'currentOpeningHours.openNow'
        return httpx.Response(200, json={'currentOpeningHours': {'openNow': True}})

    client = GoogleMapsClient('secret-key', transport=httpx.MockTransport(handler))
    status = await client.get_status('place-1')

    assert status.open_now is True


@pytest.mark.asyncio
async def test_route_uses_place_id_and_parses_duration():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen['body'] = json.loads(request.content)
        return httpx.Response(200, json={
            'routes': [{'duration': '732.4s', 'distanceMeters': 8400}]
        })

    client = GoogleMapsClient('secret-key', transport=httpx.MockTransport(handler))
    route = await client.route(Origin(latitude=40.95, longitude=-72.2), 'place-1')

    assert seen['body']['destination'] == {'placeId': 'place-1'}
    assert seen['body']['travelMode'] == 'DRIVE'
    assert seen['body']['routingPreference'] == 'TRAFFIC_AWARE'
    assert route.duration_seconds == 732
    assert route.distance_meters == 8400


@pytest.mark.asyncio
async def test_maps_http_errors_propagate_to_feasibility_boundary():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={'error': {'message': 'quota exceeded'}})

    client = GoogleMapsClient('secret-key', transport=httpx.MockTransport(handler))

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_status('place-1')
