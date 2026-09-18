import httpx

from app.clients.google_maps import RawPlace
from app.models import PlaceHint


class PhotonClient:
    """OSM-backed search client used for typo-tolerant no-key candidate retrieval."""

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        timeout: float = 8.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip('/')
        self.user_agent = user_agent.strip()
        self.timeout = timeout
        self.transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.user_agent)

    async def search_places(self, hint: PlaceHint) -> list[RawPlace]:
        if not self.enabled:
            return []

        query = ' '.join(filter(None, [hint.name, hint.address_hint, hint.city_hint]))
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.get(
                f'{self.base_url}/api/',
                params={'q': query, 'limit': 5},
                headers={'User-Agent': self.user_agent},
            )
            response.raise_for_status()
            data = response.json()

        return [
            place
            for feature in data.get('features', [])
            if (place := self._parse(feature)) is not None
        ]

    @staticmethod
    def _parse(feature: dict) -> RawPlace | None:
        properties = feature.get('properties') or {}
        geometry = feature.get('geometry') or {}
        coordinates = geometry.get('coordinates') or []

        name = properties.get('name')
        osm_type = properties.get('osm_type')
        osm_id = properties.get('osm_id')

        if not name or not osm_type or osm_id is None or len(coordinates) < 2:
            return None

        try:
            longitude = float(coordinates[0])
            latitude = float(coordinates[1])
        except (TypeError, ValueError):
            return None

        address_parts = []
        street = ' '.join(filter(None, [
            str(properties.get('housenumber') or '').strip(),
            str(properties.get('street') or '').strip(),
        ])).strip()
        for value in [
            street,
            properties.get('city'),
            properties.get('state'),
            properties.get('postcode'),
            properties.get('country'),
        ]:
            text = str(value or '').strip()
            if text and text not in address_parts:
                address_parts.append(text)

        osm_key = properties.get('osm_key')
        osm_value = properties.get('osm_value')
        provider_place_id = f'{osm_type}:{osm_id}'

        return RawPlace(
            place_id=f'photon:{provider_place_id}',
            name=str(name),
            formatted_address=', '.join(address_parts) or None,
            latitude=latitude,
            longitude=longitude,
            primary_type=str(osm_value) if osm_value else None,
            types=[str(value) for value in [osm_key, osm_value] if value],
            provider='photon',
            provider_place_id=provider_place_id,
        )
