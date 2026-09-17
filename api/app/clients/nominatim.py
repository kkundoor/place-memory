import asyncio
import time

import httpx

from app.clients.google_maps import RawPlace
from app.models import PlaceHint


class NominatimClient:
    """Rate-limited OSM geocoder used as a no-key fallback, not a POI authority."""

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        timeout: float = 8.0,
        transport: httpx.AsyncBaseTransport | None = None,
        min_interval_seconds: float = 1.0,
    ):
        self.base_url = base_url.rstrip('/')
        self.user_agent = user_agent.strip()
        self.timeout = timeout
        self.transport = transport
        self.min_interval_seconds = min_interval_seconds
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0
        self._cache: dict[str, list[RawPlace]] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.user_agent)

    async def search_places(self, hint: PlaceHint) -> list[RawPlace]:
        if not self.enabled:
            return []

        query = ', '.join(filter(None, [hint.name, hint.address_hint, hint.city_hint]))
        cached = self._cache.get(query)
        if cached is not None:
            return list(cached)

        async with self._lock:
            cached = self._cache.get(query)
            if cached is not None:
                return list(cached)

            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self.min_interval_seconds:
                await asyncio.sleep(self.min_interval_seconds - elapsed)

            async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
                response = await client.get(
                    f'{self.base_url}/search',
                    params={
                        'q': query,
                        'format': 'jsonv2',
                        'addressdetails': 1,
                        'namedetails': 1,
                        'limit': 5,
                    },
                    headers={'User-Agent': self.user_agent},
                )
                self._last_request_at = time.monotonic()
                response.raise_for_status()
                data = response.json()

            places = [place for item in data if (place := self._parse(item)) is not None]
            self._cache[query] = places
            return list(places)

    @staticmethod
    def _parse(item: dict) -> RawPlace | None:
        try:
            latitude = float(item['lat'])
            longitude = float(item['lon'])
        except (KeyError, TypeError, ValueError):
            return None

        osm_type = str(item.get('osm_type') or 'unknown')
        osm_id = str(item.get('osm_id') or '')
        if not osm_id:
            return None

        namedetails = item.get('namedetails') or {}
        address = item.get('address') or {}
        name = (
            namedetails.get('name')
            or item.get('name')
            or address.get('amenity')
            or address.get('shop')
            or str(item.get('display_name') or '').split(',')[0]
        )
        if not name:
            return None

        category = item.get('category')
        item_type = item.get('type')
        provider_place_id = f'{osm_type}:{osm_id}'
        return RawPlace(
            place_id=f'osm:{provider_place_id}',
            name=str(name),
            formatted_address=item.get('display_name'),
            latitude=latitude,
            longitude=longitude,
            primary_type=str(item_type) if item_type else None,
            types=[str(value) for value in [category, item_type] if value],
            provider='nominatim',
            provider_place_id=provider_place_id,
        )
