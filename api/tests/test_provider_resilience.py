import httpx
import pytest

from app.clients.google_maps import RawPlace
from app.clients.nominatim import NominatimClient
from app.clients.photon import PhotonClient
from app.models import PlaceHint


@pytest.mark.asyncio
async def test_photon_invalid_json_becomes_controlled_provider_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b'{"features": [',
            headers={'content-type': 'application/json'},
        )

    client = PhotonClient(
        'https://photon.test',
        'place-memory-tests/1.0',
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(httpx.HTTPError):
        await client.search_places(PlaceHint(name='Detroit Institute of Arts'))


@pytest.mark.asyncio
async def test_nominatim_invalid_json_becomes_controlled_provider_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b'[{"broken":',
            headers={'content-type': 'application/json'},
        )

    client = NominatimClient(
        'https://nominatim.test',
        'place-memory-tests/1.0',
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
    )

    with pytest.raises(httpx.HTTPError):
        await client.search_places(PlaceHint(name='Example Place'))


@pytest.mark.asyncio
async def test_nominatim_alias_lookup_skips_malformed_items():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[
            'not-a-dictionary',
            {
                'osm_type': 'node',
                'osm_id': 1,
                'name': 'Example Place',
                'namedetails': ['unexpected-shape'],
            },
        ])

    client = NominatimClient(
        'https://nominatim.test',
        'place-memory-tests/1.0',
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
    )

    place = RawPlace(
        place_id='photon:N:1',
        name='Example Place',
        formatted_address='Example City',
        latitude=42.0,
        longitude=-83.0,
        primary_type='cafe',
        types=['amenity', 'cafe'],
        provider='photon',
        provider_place_id='N:1',
    )

    aliases = await client.lookup_aliases([place])

    assert aliases == {'photon:N:1': []}


@pytest.mark.asyncio
async def test_nominatim_does_not_cache_unqueried_refs_past_batch_limit():
    requested_batches = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested_batches.append(request.url.params['osm_ids'])
        return httpx.Response(200, json=[])

    client = NominatimClient(
        'https://nominatim.test',
        'place-memory-tests/1.0',
        transport=httpx.MockTransport(handler),
        min_interval_seconds=0,
    )

    places = [
        RawPlace(
            place_id=f'photon:N:{index}',
            name=f'Place {index}',
            formatted_address='Example City',
            latitude=42.0,
            longitude=-83.0,
            primary_type='cafe',
            types=['amenity', 'cafe'],
            provider='photon',
            provider_place_id=f'N:{index}',
        )
        for index in range(1, 52)
    ]

    await client.lookup_aliases(places)

    assert len(requested_batches) == 1
    assert len(requested_batches[0].split(',')) == 50

    await client.lookup_aliases(places)

    assert len(requested_batches) == 2
    assert requested_batches[1] == 'N51'
