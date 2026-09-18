import asyncio
import math

from app.clients.google_maps import GoogleMapsClient, PlaceStatus
from app.models import FeasibleMemory, Memory, Origin


async def _unknown_status() -> PlaceStatus:
    return PlaceStatus(open_now=None)


def _google_status_place_id(memory: Memory) -> str | None:
    if not memory.place or memory.place.provider != 'google':
        return None
    return memory.place.provider_place_id or memory.place.place_id


async def check_memory(
    memory: Memory,
    origin: Origin,
    available_minutes: int,
    visit_minutes: int,
    maps: GoogleMapsClient,
) -> FeasibleMemory:
    if not memory.place:
        return FeasibleMemory(memory=memory, status='uncertain', reasons=['place is unresolved'])

    destination = Origin(
        latitude=memory.place.latitude,
        longitude=memory.place.longitude,
    )
    status_place_id = _google_status_place_id(memory)

    status_call = maps.get_status(status_place_id) if status_place_id else _unknown_status()
    route_call = maps.route(origin, destination)

    status_result, route_result = await asyncio.gather(
        status_call,
        route_call,
        return_exceptions=True,
    )

    status_failed = isinstance(status_result, BaseException)
    route_failed = isinstance(route_result, BaseException)
    open_now = None if status_failed else status_result.open_now
    duration_seconds = None if route_failed else route_result.duration_seconds
    distance_meters = None if route_failed else route_result.distance_meters
    travel_minutes = math.ceil(duration_seconds / 60) if duration_seconds is not None else None
    reasons = []

    if status_failed:
        reasons.append('opening status check failed')
    if route_failed:
        reasons.append('route check failed')

    if open_now is False:
        reasons.append('place is currently closed')
        return FeasibleMemory(
            memory=memory,
            status='no',
            travel_minutes=travel_minutes,
            distance_meters=distance_meters,
            open_now=False,
            reasons=reasons,
        )

    if travel_minutes is None:
        if not route_failed:
            reasons.append('travel time unavailable')
    elif travel_minutes * 2 + visit_minutes > available_minutes:
        reasons.append('round trip plus visit exceeds the time budget')
        return FeasibleMemory(
            memory=memory,
            status='no',
            travel_minutes=travel_minutes,
            distance_meters=distance_meters,
            open_now=open_now,
            reasons=reasons,
        )
    else:
        reasons.append('fits the current time budget')

    if open_now is None and not status_failed:
        reasons.append('live opening status unavailable')

    final_status = 'yes' if travel_minutes is not None and open_now is True else 'uncertain'
    return FeasibleMemory(
        memory=memory,
        status=final_status,
        travel_minutes=travel_minutes,
        distance_meters=distance_meters,
        open_now=open_now,
        reasons=reasons,
    )


async def check_memories(
    memories: list[Memory],
    origin: Origin,
    available_minutes: int,
    visit_minutes: int,
    maps: GoogleMapsClient,
    max_concurrency: int = 4,
) -> list[FeasibleMemory]:
    semaphore = asyncio.Semaphore(max(1, max_concurrency))

    async def guarded(memory: Memory) -> FeasibleMemory:
        async with semaphore:
            return await check_memory(memory, origin, available_minutes, visit_minutes, maps)

    results = await asyncio.gather(*(guarded(memory) for memory in memories))
    order = {'yes': 0, 'uncertain': 1, 'no': 2}
    return sorted(
        results,
        key=lambda result: (
            order[result.status],
            result.travel_minutes if result.travel_minutes is not None else 10**9,
        ),
    )
