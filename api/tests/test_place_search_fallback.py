import httpx
import pytest

from app.clients.enriched import AliasEnrichedPlaceSearchClient
from app.clients.google_maps import RawPlace
from app.models import PlaceHint


class StubProvider:
    def __init__(self, *, results=None, error=None, enabled=True):
        self.results = results or []
        self.error = error
        self.enabled = enabled
        self.calls = 0

    async def search_places(self, hint):
        self.calls += 1
        if self.error:
            raise self.error
        return self.results

    async def lookup_aliases(self, places):
        return {}


def example_place():
    return RawPlace(
        place_id='osm:node:123',
        name='Detroit Institute of Arts',
        formatted_address='Detroit, Michigan',
        latitude=42.359,
        longitude=-83.064,
        primary_type='museum',
        types=['tourism', 'museum'],
        provider='nominatim',
        provider_place_id='node:123',
    )


@pytest.mark.asyncio
async def test_nominatim_fallback_runs_when_photon_http_error():
    primary = StubProvider(error=httpx.ConnectError('photon unavailable'))
    fallback = StubProvider(results=[example_place()])
    client = AliasEnrichedPlaceSearchClient(primary, fallback, fallback_client=fallback)

    result = await client.search_places(PlaceHint(name='Detroit Institute of Arts'))
    assert [place.name for place in result] == ['Detroit Institute of Arts']
    assert primary.calls == 1
    assert fallback.calls == 1


@pytest.mark.asyncio
async def test_healthy_photon_does_not_use_fallback():
    primary = StubProvider(results=[example_place()])
    fallback = StubProvider(error=httpx.ConnectError('unused'))
    client = AliasEnrichedPlaceSearchClient(primary, fallback, fallback_client=fallback)

    result = await client.search_places(PlaceHint(name='Detroit Institute of Arts'))
    assert len(result) == 1
    assert fallback.calls == 0


@pytest.mark.asyncio
async def test_both_provider_errors_propagate():
    primary = StubProvider(error=httpx.ReadTimeout('photon timed out'))
    fallback = StubProvider(error=httpx.HTTPStatusError(
        'rate limited',
        request=httpx.Request('GET', 'https://nominatim.test/search'),
        response=httpx.Response(429),
    ))
    client = AliasEnrichedPlaceSearchClient(primary, fallback, fallback_client=fallback)

    with pytest.raises(httpx.HTTPError):
        await client.search_places(PlaceHint(name='Detroit Institute of Arts'))
    assert fallback.calls == 1


def test_enabled_when_only_fallback_enabled():
    primary = StubProvider(enabled=False)
    fallback = StubProvider(enabled=True)
    client = AliasEnrichedPlaceSearchClient(primary, fallback, fallback_client=fallback)
    assert client.enabled
