from datetime import datetime, timezone

from app.models import Memory, PlaceCandidate, ResolutionStatus, SourceType
from app.services.retrieval import search_memories


def memory(name: str, category: str) -> Memory:
    return Memory(
        id=name,
        source_type=SourceType.note,
        source_text=f'saved {name}',
        created_at=datetime.now(timezone.utc),
        resolution_status=ResolutionStatus.resolved,
        place=PlaceCandidate(
            place_id=name,
            name=name,
            latitude=0,
            longitude=0,
            primary_type=category,
            confidence=0.9,
        ),
    )


def test_query_filters_to_saved_match():
    bakery = memory('Carissa', 'bakery')
    beach = memory('Main Beach', 'beach')

    results = search_memories([bakery, beach], 'show me a bakery I saved')

    assert [item.id for item in results] == ['Carissa']
