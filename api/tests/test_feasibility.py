from datetime import datetime, timezone

import pytest

from app.clients.google_maps import PlaceStatus, RouteInfo
from app.models import Memory, Origin, PlaceCandidate, ResolutionStatus, SourceType
from app.services.feasibility import check_memory


class FakeMaps:
    def __init__(self, open_now=True, seconds=600, status_error=False, route_error=False):
        self.open_now = open_now
        self.seconds = seconds
        self.status_error = status_error
        self.route_error = route_error

    async def get_status(self, place_id):
        if self.status_error:
            raise RuntimeError('places unavailable')
        return PlaceStatus(open_now=self.open_now)

    async def route(self, origin, place_id):
        if self.route_error:
            raise RuntimeError('routes unavailable')
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


@pytest.mark.asyncio
async def test_route_failure_returns_uncertain_instead_of_crashing():
    result = await check_memory(
        saved_place(),
        Origin(latitude=40, longitude=-72),
        available_minutes=90,
        visit_minutes=45,
        maps=FakeMaps(open_now=True, route_error=True),
    )

    assert result.status == 'uncertain'
    assert result.travel_minutes is None
    assert 'route check failed' in result.reasons


@pytest.mark.asyncio
async def test_hours_failure_returns_uncertain_with_route_evidence():
    result = await check_memory(
        saved_place(),
        Origin(latitude=40, longitude=-72),
        available_minutes=90,
        visit_minutes=45,
        maps=FakeMaps(status_error=True, seconds=600),
    )

    assert result.status == 'uncertain'
    assert result.travel_minutes == 10
    assert 'opening status check failed' in result.reasons
