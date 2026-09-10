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


def test_resolution_candidates_survive_store_restart(tmp_path):
    path = tmp_path / 'candidate-memory.db'
    store = MemoryStore(str(path))
    hint = PlaceHint(name='The Point', city_hint='Southampton')
    memory = store.create(MemoryCreate(source_text='The Point in Southampton', hint=hint))
    candidates = [
        PlaceCandidate(
            place_id='bar',
            name='The Point Bar',
            formatted_address='Southampton, NY',
            latitude=40.89,
            longitude=-72.39,
            primary_type='bar',
            confidence=0.72,
        ),
        PlaceCandidate(
            place_id='cafe',
            name='The Point Cafe',
            formatted_address='Southampton, NY',
            latitude=40.89,
            longitude=-72.39,
            primary_type='cafe',
            confidence=0.70,
        ),
    ]
    store.update_resolution(
        memory.id,
        hint,
        candidates[0],
        ResolutionStatus.needs_review,
        candidates,
    )

    saved = MemoryStore(str(path)).get(memory.id)

    assert saved is not None
    assert saved.resolution_status == ResolutionStatus.needs_review
    assert [item.place_id for item in saved.candidates] == ['bar', 'cafe']


def test_store_migrates_pre_candidate_schema(tmp_path):
    import sqlite3

    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as conn:
        conn.execute(
            '''
            create table memories (
                id text primary key,
                source_type text not null,
                source_text text not null,
                source_url text,
                note text,
                created_at text not null,
                resolution_status text not null,
                hint_json text,
                place_json text
            )
            '''
        )

    store = MemoryStore(str(path))
    memory = store.create(MemoryCreate(source_text='legacy schema still works'))

    with sqlite3.connect(path) as conn:
        columns = {row[1] for row in conn.execute('pragma table_info(memories)').fetchall()}

    assert 'candidates_json' in columns
    assert store.get(memory.id).candidates == []


def test_delete_memory_is_persistent(tmp_path):
    path = tmp_path / 'delete.db'
    store = MemoryStore(str(path))
    memory = store.create(MemoryCreate(source_text='remove me'))

    assert store.delete(memory.id) is True
    assert MemoryStore(str(path)).get(memory.id) is None
    assert store.delete(memory.id) is False
