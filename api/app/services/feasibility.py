import asyncio
import math

from app.clients.google_maps import GoogleMapsClient
from app.models import FeasibleMemory, Memory, Origin


async def check_memory(
    memory: Memory,
    origin: Origin,
    available_minutes: int,
    visit_minutes: int,
    maps: GoogleMapsClient,
) -> FeasibleMemory:
    if not memory.place:
        return FeasibleMemory(memory=memory, status='uncertain', reasons=['place is unresolved'])

    status_task = maps.get_status(memory.place.place_id)
    route_task = maps.route(origin, memory.place.place_id)
    place_status, route = await asyncio.gather(status_task, route_task)

    travel_minutes = math.ceil(route.duration_seconds / 60) if route.duration_seconds is not None else None
    reasons = []

    if place_status.open_now is False:
        return FeasibleMemory(
            memory=memory,
            status='no',
            travel_minutes=travel_minutes,
            distance_meters=route.distance_meters,
            open_now=False,
            reasons=['place is currently closed'],
        )

    if travel_minutes is None:
        reasons.append('travel time unavailable')
    elif travel_minutes * 2 + visit_minutes > available_minutes:
        reasons.append('round trip plus visit exceeds the time budget')
        return FeasibleMemory(
            memory=memory,
            status='no',
            travel_minutes=travel_minutes,
            distance_meters=route.distance_meters,
            open_now=place_status.open_now,
            reasons=reasons,
        )
    else:
        reasons.append('fits the current time budget')

    if place_status.open_now is None:
        reasons.append('live opening status unavailable')

    final_status = 'yes' if travel_minutes is not None and place_status.open_now is True else 'uncertain'
    return FeasibleMemory(
        memory=memory,
        status=final_status,
        travel_minutes=travel_minutes,
        distance_meters=route.distance_meters,
        open_now=place_status.open_now,
        reasons=reasons,
    )
