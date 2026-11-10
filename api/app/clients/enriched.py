from dataclasses import replace
import logging

import httpx

from app.clients.google_maps import RawPlace
from app.models import PlaceHint


logger = logging.getLogger('place_memory.place_search')


class AliasEnrichedPlaceSearchClient:
    """Photon search with optional Nominatim failover and best-effort OSM aliases."""

    def __init__(self, search_client, alias_client, fallback_client=None):
        self.search_client = search_client
        self.alias_client = alias_client
        self.fallback_client = fallback_client

    @property
    def enabled(self) -> bool:
        return bool(
            self.search_client.enabled
            or (self.fallback_client is not None and self.fallback_client.enabled)
        )

    async def search_places(self, hint: PlaceHint) -> list[RawPlace]:
        try:
            places = await self.search_client.search_places(hint)
        except httpx.HTTPError as primary_error:
            if self.fallback_client is None or not self.fallback_client.enabled:
                raise

            logger.warning(
                'primary_place_search_failed provider=photon error_type=%s; trying_fallback=nominatim',
                type(primary_error).__name__,
            )
            try:
                return await self.fallback_client.search_places(hint)
            except httpx.HTTPError as fallback_error:
                logger.error(
                    'fallback_place_search_failed provider=nominatim error_type=%s',
                    type(fallback_error).__name__,
                )
                raise fallback_error from primary_error

        if not places or not self.alias_client.enabled:
            return places

        try:
            aliases_by_place = await self.alias_client.lookup_aliases(places)
        except httpx.HTTPError:
            logger.exception('alias_lookup_failed')
            return places

        return [
            replace(place, aliases=aliases_by_place.get(place.place_id, place.aliases))
            for place in places
        ]
