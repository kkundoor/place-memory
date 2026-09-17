import asyncio
import time

import httpx

from app.clients.google_maps import RawPlace
from app.models import PlaceHint


class NominatimClient:
    def __init__(
        self,
        base_url: str,
        user_agent: str,
        timeout: float = 8.0,
        min_interval_seconds: float = 1.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip('/')
        self.user_agent = user_agent
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self.transport = transport
        self._cache: dict[str, list[RawPlace]] = {}
        self._request_lock = asyncio.Lock()
        self._last_request_at = 0.0

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.user_agent)

    async def search_places(self, hint: PlaceHint) -> list[RawPlace]:
        if not self.enabled:
            return []

        query = ', '.join(filter(None, [
            hint.name,
            hint.address_hint,
            hint.city_hint,
        ]))

        cached = self._cache.get(query)
        if cached is not None:
            return list(cached)

        params = {
            'q': query,
            'format': 'jsonv2',
            'addressdetails': 1,
            'namedetails': 1,
            'limit': 5,
        }
        headers = {
            'User-Agent': self.user_agent,
        }

        async with self._request_lock:
            elapsed = time.monotonic() - self._last_request_at
            wait_seconds = self.min_interval_seconds - elapsed
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    f'{self.base_url}/search',
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

            self._last_request_at = time.monotonic()

        places = [
            place
            for item in data
            if (place := self._parse_place(item)) is not None
        ]
        self._cache[query] = places
        return list(places)

    @staticmethod
    def _parse_place(item: dict) -> RawPlace | None:
        if not item.get('lat') or not item.get('lon'):
            return None

        name = NominatimClient._place_name(item)
        if not name:
            return None

        category = item.get('category')
        place_type = item.get('type')
        types = list(dict.fromkeys(
            value
            for value in [category, place_type]
            if value
        ))

        osm_type = item.get('osm_type')
        osm_id = item.get('osm_id')
        if osm_type and osm_id:
            place_id = f'osm:{osm_type}:{osm_id}'
        else:
            place_id = f'nominatim:{item["place_id"]}'

        return RawPlace(
            place_id=place_id,
            name=name,
            formatted_address=item.get('display_name'),
            latitude=float(item['lat']),
            longitude=float(item['lon']),
            primary_type=place_type,
            types=types,
        )

    @staticmethod
    def _place_name(item: dict) -> str:
        names = item.get('namedetails') or {}
        if names.get('name'):
            return str(names['name'])

        address = item.get('address') or {}
        for key in (
            'shop',
            'amenity',
            'tourism',
            'leisure',
            'office',
            'craft',
            'building',
            'place',
        ):
            if address.get(key):
                return str(address[key])

        display_name = str(item.get('display_name') or '')
        return display_name.split(',')[0].strip()