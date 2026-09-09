from app.models import MemoryCreate, PlaceCandidate, PlaceHint, ResolutionStatus, SourceType
from app.storage.sqlite import MemoryStore


def test_memory_round_trip_survives_store_restart(tmp_path):
    path = tmp_path / 'memories.db'
    first = MemoryStore(str(path))
    memory = first.create(MemoryCreate(
        source_type=SourceType.screenshot,
        source_text='saved bakery screenshot',
        note='try this weekend',
        hint=PlaceHint(name='Carissa’s Bakery', city_hint='East Hampton'),
    ))
    first.update_resolution(
        memory.id,
        memory.hint,
        PlaceCandidate(
            place_id='place-1',
            name='Carissa’s Bakery',
            formatted_address='East Hampton, NY',
            latitude=40.96,
            longitude=-72.18,
            primary_type='bakery',
            types=['bakery', 'food'],
            confidence=0.91,
            confidence_reasons=['name=1.00', 'location=0.90'],
        ),
        ResolutionStatus.resolved,
    )

    reopened = MemoryStore(str(path))
    saved = reopened.get(memory.id)

    assert saved is not None
    assert saved.resolution_status == ResolutionStatus.resolved
    assert saved.hint.name == 'Carissa’s Bakery'
    assert saved.place.place_id == 'place-1'
    assert saved.place.confidence_reasons == ['name=1.00', 'location=0.90']
    assert saved.note == 'try this weekend'
