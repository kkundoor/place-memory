import pytest
from fastapi.testclient import TestClient

from app import main
from app.storage.sqlite import MemoryStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'store', MemoryStore(str(tmp_path / 'test.db')))
    return TestClient(main.app)


def test_local_ingest_review_confirm_and_query(client):
    response = client.post('/api/memories/ingest', json={
        'source_type': 'note',
        'source_text': 'Carissa’s Bakery in East Hampton',
        'hint': {
            'name': 'Carissa’s Bakery',
            'city_hint': 'East Hampton',
            'category_hint': 'bakery',
        },
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload['memory']['resolution_status'] == 'unresolved'
    assert payload['warning'] == 'google maps is not configured'

    memory_id = payload['memory']['id']
    confirm = client.post(f'/api/memories/{memory_id}/confirm', json={
        'place_id': 'place-1',
        'name': 'Carissa’s Bakery',
        'formatted_address': 'East Hampton, NY',
        'latitude': 40.96,
        'longitude': -72.18,
        'primary_type': 'bakery',
        'types': ['bakery', 'food'],
        'confidence': 0.82,
        'confidence_reasons': ['manual confirmation'],
    })

    assert confirm.status_code == 200
    assert confirm.json()['resolution_status'] == 'resolved'
    assert confirm.json()['place']['confidence'] == 1.0

    query = client.get('/api/memories', params={'q': 'bakery'})

    assert query.status_code == 200
    assert [item['place']['name'] for item in query.json()] == ['Carissa’s Bakery']


def test_local_feasibility_is_uncertain_without_live_maps(client):
    create = client.post('/api/memories', json={
        'source_type': 'note',
        'source_text': 'saved lunch place',
        'hint': {'name': 'Lunch Place'},
    })
    memory_id = create.json()['id']
    client.post(f'/api/memories/{memory_id}/confirm', json={
        'place_id': 'place-2',
        'name': 'Lunch Place',
        'latitude': 40.90,
        'longitude': -72.30,
        'confidence': 0.9,
    })

    response = client.post('/api/feasible', json={
        'origin': {'latitude': 40.90, 'longitude': -72.30},
        'available_minutes': 90,
        'visit_minutes': 45,
    })

    assert response.status_code == 200
    result = response.json()['results'][0]
    assert result['status'] == 'uncertain'
    assert 'travel time unavailable' in result['reasons']
    assert 'live opening status unavailable' in result['reasons']


def test_review_candidates_are_persisted(client, monkeypatch):
    from app.clients.google_maps import RawPlace

    class ReviewMaps:
        enabled = True

        async def search_places(self, hint):
            return [
                RawPlace(
                    place_id='bar',
                    name='The Point Bar',
                    formatted_address='Southampton, NY',
                    latitude=40.89,
                    longitude=-72.39,
                    primary_type='bar',
                    types=['bar'],
                ),
                RawPlace(
                    place_id='cafe',
                    name='The Point Cafe',
                    formatted_address='Southampton, NY',
                    latitude=40.89,
                    longitude=-72.39,
                    primary_type='cafe',
                    types=['cafe'],
                ),
            ]

    monkeypatch.setattr(main, 'maps', ReviewMaps())
    response = client.post('/api/memories/ingest', json={
        'source_type': 'note',
        'source_text': 'The Point in Southampton',
        'hint': {'name': 'The Point', 'city_hint': 'Southampton'},
    })

    assert response.status_code == 200
    memory = response.json()['memory']
    assert memory['resolution_status'] == 'needs_review'
    assert [item['place_id'] for item in memory['candidates']] == ['bar', 'cafe']

    listed = client.get('/api/memories').json()
    saved = next(item for item in listed if item['id'] == memory['id'])
    assert [item['place_id'] for item in saved['candidates']] == ['bar', 'cafe']


def test_confirm_uses_stored_candidate_instead_of_client_fields(client, monkeypatch):
    from app.clients.google_maps import RawPlace

    class ReviewMaps:
        enabled = True

        async def search_places(self, hint):
            return [
                RawPlace(
                    place_id='bar',
                    name='The Point Bar',
                    formatted_address='Southampton, NY',
                    latitude=40.89,
                    longitude=-72.39,
                    primary_type='bar',
                    types=['bar'],
                ),
                RawPlace(
                    place_id='cafe',
                    name='The Point Cafe',
                    formatted_address='Southampton, NY',
                    latitude=40.89,
                    longitude=-72.39,
                    primary_type='cafe',
                    types=['cafe'],
                ),
            ]

    monkeypatch.setattr(main, 'maps', ReviewMaps())
    ingest = client.post('/api/memories/ingest', json={
        'source_text': 'The Point in Southampton',
        'hint': {'name': 'The Point', 'city_hint': 'Southampton'},
    }).json()
    memory_id = ingest['memory']['id']

    confirm = client.post(f'/api/memories/{memory_id}/confirm', json={
        'place_id': 'cafe',
        'name': 'tampered name',
        'formatted_address': 'wrong address',
        'latitude': 0,
        'longitude': 0,
        'confidence': 0.1,
    })

    assert confirm.status_code == 200
    place = confirm.json()['place']
    assert place['name'] == 'The Point Cafe'
    assert place['formatted_address'] == 'Southampton, NY'
    assert place['latitude'] == 40.89
    assert place['confidence'] == 1.0
    assert place['confidence_reasons'][-1] == 'confirmed by user'


def test_confirm_rejects_candidate_that_was_not_offered(client, monkeypatch):
    from app.clients.google_maps import RawPlace

    class ReviewMaps:
        enabled = True

        async def search_places(self, hint):
            return [
                RawPlace(
                    place_id='bar',
                    name='The Point Bar',
                    formatted_address='Southampton, NY',
                    latitude=40.89,
                    longitude=-72.39,
                    primary_type='bar',
                    types=['bar'],
                ),
                RawPlace(
                    place_id='cafe',
                    name='The Point Cafe',
                    formatted_address='Southampton, NY',
                    latitude=40.89,
                    longitude=-72.39,
                    primary_type='cafe',
                    types=['cafe'],
                ),
            ]

    monkeypatch.setattr(main, 'maps', ReviewMaps())
    ingest = client.post('/api/memories/ingest', json={
        'source_text': 'The Point in Southampton',
        'hint': {'name': 'The Point', 'city_hint': 'Southampton'},
    }).json()
    memory_id = ingest['memory']['id']

    confirm = client.post(f'/api/memories/{memory_id}/confirm', json={
        'place_id': 'not-offered',
        'name': 'Other Place',
        'latitude': 0,
        'longitude': 0,
        'confidence': 0.1,
    })

    assert confirm.status_code == 400
    assert confirm.json()['detail'] == 'candidate was not offered for review'


def test_request_metadata_adds_trace_id_without_echoing_query(client, caplog):
    caplog.set_level('INFO', logger='place_memory.api')
    response = client.get('/api/memories?q=private-trip-note', headers={'x-request-id': 'test-request'})

    assert response.status_code == 200
    assert response.headers['x-request-id'] == 'test-request'
    log_text = ' '.join(record.getMessage() for record in caplog.records)
    assert 'request_id=test-request' in log_text
    assert 'path=/api/memories' in log_text
    assert 'private-trip-note' not in log_text


def test_confirm_rejects_invalid_coordinates(client):
    create = client.post('/api/memories', json={
        'source_text': 'saved place',
        'hint': {'name': 'Saved Place'},
    })
    memory_id = create.json()['id']

    response = client.post(f'/api/memories/{memory_id}/confirm', json={
        'place_id': 'place-1',
        'name': 'Saved Place',
        'latitude': 120,
        'longitude': -72,
        'confidence': 0.9,
    })

    assert response.status_code == 422
