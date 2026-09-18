import asyncio
import re
import time

import httpx

from app.clients.google_maps import RawPlace
from app.models import PlaceHint


_ALIAS_KEYS = ('old_name', 'alt_name', 'loc_name', 'short_name', 'official_name')
_LANGUAGE_NAME_KEY = re.compile(
    r'^name:[a-z]{2,3}(?:[-_][a-z0-9]{2,8})*$',
    re.IGNORECASE,
)
_LANGUAGE_ALIAS_SUFFIX = re.compile(
    r'^[a-z]{2,3}(?:[-_][a-z0-9]{2,8})*$',
    re.IGNORECASE,
)


class NominatimClient:
    """Rate-limited OSM geocoder and metadata lookup client."""

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
        self._alias_cache: dict[str, list[str]] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.user_agent)

    async def _get_json(self, path: str, params: dict) -> object:
        async with self._lock:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self.min_interval_seconds:
                await asyncio.sleep(self.min_interval_seconds - elapsed)

            async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
                response = await client.get(
                    f'{self.base_url}{path}',
                    params=params,
                    headers={'User-Agent': self.user_agent},
                )
                self._last_request_at = time.monotonic()
                response.raise_for_status()
                return response.json()

    async def search_places(self, hint: PlaceHint) -> list[RawPlace]:
        if not self.enabled:
            return []

        query = ', '.join(filter(None, [hint.name, hint.address_hint, hint.city_hint]))
        cached = self._cache.get(query)
        if cached is not None:
            return list(cached)

        data = await self._get_json('/search', {
            'q': query,
            'format': 'jsonv2',
            'addressdetails': 1,
            'namedetails': 1,
            'limit': 5,
        })
        places = [place for item in data if (place := self._parse(item)) is not None]
        self._cache[query] = places
        return list(places)

    async def lookup_aliases(self, places: list[RawPlace]) -> dict[str, list[str]]:
        """Return historical/alternate names keyed by RawPlace.place_id."""
        if not self.enabled or not places:
            return {}

        place_by_ref: dict[str, RawPlace] = {}
        for place in places:
            ref = self._lookup_ref(place)
            if ref:
                place_by_ref[ref] = place

        missing = [ref for ref in place_by_ref if ref not in self._alias_cache]
        if missing:
            data = await self._get_json('/lookup', {
                'osm_ids': ','.join(missing[:50]),
                'format': 'jsonv2',
                'namedetails': 1,
                'addressdetails': 0,
            })

            seen: set[str] = set()
            for item in data:
                ref = self._item_ref(item)
                if not ref:
                    continue
                seen.add(ref)
                canonical = str((item.get('namedetails') or {}).get('name') or item.get('name') or '')
                self._alias_cache[ref] = self._extract_aliases(item.get('namedetails') or {}, canonical)

            for ref in missing:
                if ref not in seen:
                    self._alias_cache[ref] = []

        return {
            place.place_id: list(self._alias_cache.get(ref, []))
            for ref, place in place_by_ref.items()
        }

    @staticmethod
    def _extract_aliases(namedetails: dict, canonical: str) -> list[str]:
        aliases: list[str] = []
        seen = {canonical.casefold()} if canonical else set()

        for key, value in namedetails.items():
            key_text = str(key).lower()
            is_language_name = bool(_LANGUAGE_NAME_KEY.fullmatch(key_text))
            is_alias_key = key_text in _ALIAS_KEYS or any(
                key_text.startswith(f'{item}:')
                and _LANGUAGE_ALIAS_SUFFIX.fullmatch(
                    key_text[len(item) + 1:]
                )
                for item in _ALIAS_KEYS
            )
            if not (is_language_name or is_alias_key):
                continue

            for part in str(value or '').split(';'):
                alias = part.strip()
                folded = alias.casefold()
                if alias and folded not in seen:
                    aliases.append(alias)
                    seen.add(folded)

        return aliases

    @staticmethod
    def _lookup_ref(place: RawPlace) -> str | None:
        value = place.provider_place_id or place.place_id
        match = re.search(r'(?:^|:)(N|W|R|node|way|relation):?(\d+)$', value, re.I)
        if not match:
            return None
        prefix = {
            'node': 'N',
            'way': 'W',
            'relation': 'R',
        }.get(match.group(1).lower(), match.group(1).upper())
        return f'{prefix}{match.group(2)}'

    @staticmethod
    def _item_ref(item: dict) -> str | None:
        osm_type = str(item.get('osm_type') or '')
        osm_id = str(item.get('osm_id') or '')
        if not osm_id:
            return None
        prefix = {
            'node': 'N',
            'way': 'W',
            'relation': 'R',
        }.get(osm_type.lower(), osm_type.upper())
        return f'{prefix}{osm_id}' if prefix in {'N', 'W', 'R'} else None

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
            aliases=NominatimClient._extract_aliases(namedetails, str(name)),
            formatted_address=item.get('display_name'),
            latitude=latitude,
            longitude=longitude,
            primary_type=str(item_type) if item_type else None,
            types=[str(value) for value in [category, item_type] if value],
            provider='nominatim',
            provider_place_id=provider_place_id,
        )
