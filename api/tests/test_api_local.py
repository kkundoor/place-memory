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
