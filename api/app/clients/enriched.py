from dataclasses import replace
import logging

import httpx

from app.clients.google_maps import RawPlace
from app.models import PlaceHint


logger = logging.getLogger('place_memory.place_search')


class AliasEnrichedPlaceSearchClient:
    """Search with one provider, then enrich returned OSM objects with alternate names."""

    def __init__(self, search_client, alias_client):
        self.search_client = search_client
        self.alias_client = alias_client

    @property
    def enabled(self) -> bool:
        return bool(self.search_client.enabled)

    async def search_places(self, hint: PlaceHint) -> list[RawPlace]:
        places = await self.search_client.search_places(hint)
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
