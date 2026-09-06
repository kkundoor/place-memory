from datetime import datetime, timezone

import pytest

from app.clients.google_maps import PlaceStatus, RouteInfo
from app.models import Memory, Origin, PlaceCandidate, ResolutionStatus, SourceType
from app.services.feasibility import check_memory


class FakeMaps:
    def __init__(self, open_now=True, seconds=600):
        self.open_now = open_now
        self.seconds = seconds

    async def get_status(self, place_id):
        return PlaceStatus(open_now=self.open_now)

    async def route(self, origin, place_id):
        return RouteInfo(duration_seconds=self.seconds, distance_meters=5000)


def saved_place() -> Memory:
    return Memory(
        id='1',
        source_type=SourceType.note,
        source_text='saved lunch',
        created_at=datetime.now(timezone.utc),
        resolution_status=ResolutionStatus.resolved,
        place=PlaceCandidate(
            place_id='place-1',
            name='Lunch',
            latitude=40,
            longitude=-72,
            confidence=0.9,
        ),
    )


@pytest.mark.asyncio
async def test_feasible_when_open_and_inside_budget():
    result = await check_memory(
        saved_place(),
        Origin(latitude=40, longitude=-72),
        available_minutes=90,
        visit_minutes=45,
        maps=FakeMaps(open_now=True, seconds=600),
    )

    assert result.status == 'yes'
    assert result.travel_minutes == 10


@pytest.mark.asyncio
async def test_closed_place_is_not_feasible():
    result = await check_memory(
        saved_place(),
        Origin(latitude=40, longitude=-72),
        available_minutes=90,
        visit_minutes=45,
        maps=FakeMaps(open_now=False, seconds=600),
    )

    assert result.status == 'no'
    assert result.open_now is False
