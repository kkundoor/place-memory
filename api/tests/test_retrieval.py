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


def test_context_only_query_keeps_all_candidates_for_feasibility():
    bakery = memory('Carissa', 'bakery')
    beach = memory('Main Beach', 'beach')

    results = search_memories([bakery, beach], 'what can I do in the next 90 minutes?')

    assert {item.id for item in results} == {'Carissa', 'Main Beach'}


def test_specific_query_with_no_match_does_not_return_everything():
    bakery = memory('Carissa', 'bakery')
    beach = memory('Main Beach', 'beach')

    results = search_memories([bakery, beach], 'show me a coffee shop I saved')

    assert results == []


def test_context_query_can_include_numeric_time_budget():
    bakery = memory('Carissa', 'bakery')
    beach = memory('Main Beach', 'beach')

    results = search_memories([bakery, beach], 'what is doable nearby in the next 90 minutes?')

    assert {item.id for item in results} == {'Carissa', 'Main Beach'}
