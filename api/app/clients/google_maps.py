from dataclasses import dataclass, field

import httpx

from app.models import Origin, PlaceHint


@dataclass
class RawPlace:
    place_id: str
    name: str
    formatted_address: str | None
    latitude: float
    longitude: float
    primary_type: str | None
    types: list[str]
    provider: str = 'google'
    provider_place_id: str | None = None
    aliases: list[str] = field(default_factory=list)


@dataclass
class PlaceStatus:
    open_now: bool | None


@dataclass
class RouteInfo:
    duration_seconds: int | None
    distance_meters: int | None


class GoogleMapsClient:
    def __init__(
        self,
        api_key: str,
        timeout: float = 8.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self.transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search_places(self, hint: PlaceHint) -> list[RawPlace]:
        if not self.enabled:
            return []

        query = ', '.join(filter(None, [hint.name, hint.address_hint, hint.city_hint]))
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.api_key,
            'X-Goog-FieldMask': ','.join([
                'places.id',
                'places.displayName',
                'places.formattedAddress',
                'places.location',
                'places.primaryType',
                'places.types',
            ]),
        }
        body = {'textQuery': query, 'maxResultCount': 5}

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(
                'https://places.googleapis.com/v1/places:searchText',
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get('places', []):
            location = item.get('location') or {}
            if 'latitude' not in location or 'longitude' not in location:
                continue
            results.append(RawPlace(
                place_id=item['id'],
                name=(item.get('displayName') or {}).get('text', ''),
                formatted_address=item.get('formattedAddress'),
                latitude=location['latitude'],
                longitude=location['longitude'],
                primary_type=item.get('primaryType'),
                types=item.get('types', []),
                provider='google',
                provider_place_id=item['id'],
            ))
        return results

    async def get_status(self, place_id: str) -> PlaceStatus:
        if not self.enabled:
            return PlaceStatus(open_now=None)

        headers = {
            'X-Goog-Api-Key': self.api_key,
            'X-Goog-FieldMask': 'currentOpeningHours.openNow',
        }
        url = f'https://places.googleapis.com/v1/places/{place_id}'
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
        hours = data.get('currentOpeningHours') or {}
        return PlaceStatus(open_now=hours.get('openNow'))

    async def static_map(self, origin: Origin, places: list[tuple[float, float]]) -> bytes | None:
        if not self.enabled:
            return None

        params: list[tuple[str, str]] = [
            ('size', '640x360'),
            ('scale', '2'),
            ('maptype', 'roadmap'),
            ('key', self.api_key),
            ('markers', f'label:U|{origin.latitude},{origin.longitude}'),
        ]
        for latitude, longitude in places[:12]:
            params.append(('markers', f'{latitude},{longitude}'))

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.get(
                'https://maps.googleapis.com/maps/api/staticmap',
                params=params,
            )
            response.raise_for_status()
            return response.content

    async def route(self, origin: Origin, place_id: str) -> RouteInfo:
        if not self.enabled:
            return RouteInfo(duration_seconds=None, distance_meters=None)

        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.api_key,
            'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters',
        }
        body = {
            'origin': {'location': {'latLng': {
                'latitude': origin.latitude,
                'longitude': origin.longitude,
            }}},
            'destination': {'placeId': place_id},
            'travelMode': 'DRIVE',
            'routingPreference': 'TRAFFIC_AWARE',
        }
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(
                'https://routes.googleapis.com/directions/v2:computeRoutes',
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        routes = data.get('routes') or []
        if not routes:
            return RouteInfo(duration_seconds=None, distance_meters=None)
        first = routes[0]
        duration = first.get('duration')
        seconds = int(float(duration[:-1])) if isinstance(duration, str) and duration.endswith('s') else None
        return RouteInfo(
            duration_seconds=seconds,
            distance_meters=first.get('distanceMeters'),
        )
