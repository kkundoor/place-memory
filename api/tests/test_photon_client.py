import httpx
import pytest

from app.clients.photon import PhotonClient
from app.models import PlaceHint


@pytest.mark.asyncio
async def test_photon_builds_search_query_and_normalizes_results():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen['query'] = request.url.params['q']
        seen['limit'] = request.url.params['limit']
        seen['user_agent'] = request.headers['user-agent']
        return httpx.Response(200, json={
            'features': [{
                'geometry': {
                    'coordinates': [-83.7451513, 42.2846981],
                },
                'properties': {
                    'name': "Zingerman's Deli",
                    'housenumber': '422',
                    'street': 'Detroit Street',
                    'city': 'Ann Arbor',
                    'state': 'Michigan',
                    'postcode': '48104',
                    'country': 'United States',
                    'osm_key': 'amenity',
                    'osm_value': 'restaurant',
                    'osm_type': 'N',
                    'osm_id': 12552300476,
                },
            }],
        })

    client = PhotonClient(
        'https://photon.test',
        'place-memory-tests/1.0',
        transport=httpx.MockTransport(handler),
    )

    results = await client.search_places(PlaceHint(
        name='Zingermans Delicatessen',
        city_hint='Ann Arbor',
        category_hint='delicatessen',
    ))

    assert seen['query'] == 'Zingermans Delicatessen Ann Arbor'
    assert seen['limit'] == '5'
    assert seen['user_agent'] == 'place-memory-tests/1.0'
    assert len(results) == 1

    result = results[0]
    assert result.place_id == 'photon:N:12552300476'
    assert result.provider == 'photon'
    assert result.provider_place_id == 'N:12552300476'
    assert result.name == "Zingerman's Deli"
    assert result.formatted_address == '422 Detroit Street, Ann Arbor, Michigan, 48104, United States'
    assert result.latitude == 42.2846981
    assert result.longitude == -83.7451513
    assert result.primary_type == 'restaurant'
    assert result.types == ['amenity', 'restaurant']


@pytest.mark.asyncio
async def test_photon_ignores_features_without_identity_or_coordinates():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            'features': [
                {'geometry': {'coordinates': [-83.7, 42.2]}, 'properties': {}},
                {'geometry': {'coordinates': []}, 'properties': {
                    'name': 'Broken Place',
                    'osm_type': 'N',
                    'osm_id': 1,
                }},
            ],
        })

    client = PhotonClient(
        'https://photon.test',
        'place-memory-tests/1.0',
        transport=httpx.MockTransport(handler),
    )

    results = await client.search_places(PlaceHint(name='Broken Place'))

    assert results == []
