import pytest
from fastapi.testclient import TestClient

from app import main
from app.storage.sqlite import MemoryStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    class DisabledPlaceSearch:
        enabled = False

        async def search_places(self, hint):
            return []

    monkeypatch.setattr(main, 'store', MemoryStore(str(tmp_path / 'test.db')))
    monkeypatch.setattr(main, 'place_search', DisabledPlaceSearch())
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
    assert payload['warning'] == 'place search is not configured'

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
    assert confirm.json()['resolution_method'] == 'manual'
    assert confirm.json()['place']['confidence'] == 0.82

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

    monkeypatch.setattr(main, 'place_search', ReviewMaps())
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

    monkeypatch.setattr(main, 'place_search', ReviewMaps())
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
    assert place['confidence'] < 1.0
    assert place['confidence_reasons'][-1] == 'confirmed by user'
    assert confirm.json()['resolution_method'] == 'manual'


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

    monkeypatch.setattr(main, 'place_search', ReviewMaps())
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


def test_delete_memory_removes_saved_data(client):
    create = client.post('/api/memories', json={'source_text': 'temporary save'})
    memory_id = create.json()['id']

    response = client.delete(f'/api/memories/{memory_id}')

    assert response.status_code == 204
    assert all(item['id'] != memory_id for item in client.get('/api/memories').json())
    assert client.delete(f'/api/memories/{memory_id}').status_code == 404


def test_unicode_survives_api_serialization(client):
    create = client.post('/api/memories', json={
        'source_text': "saved Zingerman's Next Door Café in Quindío",
        'hint': {'name': "Zingerman's Next Door Café", 'city_hint': 'Quindío'},
    })
    assert create.status_code == 200
    body = client.get('/api/memories').json()[0]
    assert body['source_text'] == "saved Zingerman's Next Door Café in Quindío"
    assert body['hint']['name'] == "Zingerman's Next Door Café"
    assert body['hint']['city_hint'] == 'Quindío'


def test_reject_candidates_marks_memory_abstained(client, monkeypatch):
    from app.clients.google_maps import RawPlace

    class ReviewSearch:
        enabled = True
        async def search_places(self, hint):
            return [
                RawPlace(place_id='one', name='The Point Bar', formatted_address='Southampton, NY', latitude=40.89, longitude=-72.39, primary_type='bar', types=['bar']),
                RawPlace(place_id='two', name='The Point Cafe', formatted_address='Southampton, NY', latitude=40.89, longitude=-72.39, primary_type='cafe', types=['cafe']),
            ]

    monkeypatch.setattr(main, 'place_search', ReviewSearch())
    ingest = client.post('/api/memories/ingest', json={
        'source_text': 'The Point in Southampton',
        'hint': {'name': 'The Point', 'city_hint': 'Southampton'},
    }).json()
    response = client.post(f"/api/memories/{ingest['memory']['id']}/reject")
    assert response.status_code == 200
    body = response.json()
    assert body['resolution_status'] == 'unresolved'
    assert body['resolution_method'] == 'abstained'
    assert body['place'] is None


def test_image_ingest_rejects_unsupported_media_before_model(client):
    response = client.post(
        '/api/memories/ingest-image',
        files={'image': ('save.gif', b'GIF89a', 'image/gif')},
    )

    assert response.status_code == 415
    assert response.json()['detail'] == 'jpeg, png, or webp required'


def test_image_ingest_rejects_oversize_upload_before_model(client):
    response = client.post(
        '/api/memories/ingest-image',
        files={'image': ('save.png', b'x' * (8 * 1024 * 1024 + 1), 'image/png')},
    )

    assert response.status_code == 413
    assert response.json()['detail'] == 'image must be under 8 MB'


def test_resolution_explanation_exposes_policy_and_candidate_reasons(client, monkeypatch):
    from app.clients.google_maps import RawPlace

    class Search:
        enabled = True

        async def search_places(self, hint):
            return [
                RawPlace(
                    place_id='known-place',
                    name='Carissa’s Bakery',
                    formatted_address='East Hampton, NY',
                    latitude=40.96,
                    longitude=-72.18,
                    primary_type='bakery',
                    types=['bakery'],
                    provider='fixture',
                    provider_place_id='known-place',
                )
            ]

    monkeypatch.setattr(main, 'place_search', Search())
    ingest = client.post('/api/memories/ingest', json={
        'source_text': 'Carissa’s Bakery in East Hampton',
        'hint': {
            'name': 'Carissa’s Bakery',
            'city_hint': 'East Hampton',
            'category_hint': 'bakery',
        },
    }).json()

    response = client.get(f"/api/memories/{ingest['memory']['id']}/resolution")

    assert response.status_code == 200
    body = response.json()
    assert body['policy']['resolve_threshold'] == 0.76
    assert body['status'] == 'resolved'
    assert body['candidates'][0]['provider'] == 'fixture'
    assert any(reason.startswith('name=') for reason in body['candidates'][0]['confidence_reasons'])


def test_ingest_keeps_memory_unresolved_when_place_provider_fails(client, monkeypatch):
    import httpx

    class FailingSearch:
        enabled = True

        async def search_places(self, hint):
            raise httpx.ConnectError('provider offline')

    monkeypatch.setattr(main, 'place_search', FailingSearch())
    response = client.post('/api/memories/ingest', json={
        'source_text': 'Detroit Institute of Arts',
        'hint': {'name': 'Detroit Institute of Arts', 'city_hint': 'Detroit'},
    })

    assert response.status_code == 200
    body = response.json()
    assert body['memory']['resolution_status'] == 'unresolved'
    assert body['candidates'] == []
    assert body['warning'] == 'place search is temporarily unavailable'


def test_text_ingest_does_not_persist_partial_memory_when_extraction_fails(client, monkeypatch):
    class FailingExtractor:
        async def extract_text(self, text):
            raise RuntimeError('gemini request failed; retry shortly')

    monkeypatch.setattr(main, 'extractor', FailingExtractor())

    response = client.post('/api/memories/ingest', json={
        'source_type': 'note',
        'source_text': 'Michigan Stadium in Ann Arbor',
    })

    assert response.status_code == 503
    assert response.json()['detail'] == 'gemini request failed; retry shortly'
    assert client.get('/api/memories').json() == []


def test_text_ingest_runs_extraction_resolution_and_persistence(client, monkeypatch):
    from app.clients.google_maps import RawPlace
    from app.models import PlaceHint

    class Extractor:
        async def extract_text(self, text):
            assert 'Detroit Institute of Arts' in text
            return PlaceHint(
                name='Detroit Institute of Arts',
                city_hint='Detroit',
                category_hint='museum',
                evidence='Detroit Institute of Arts',
            )

    class Search:
        enabled = True

        async def search_places(self, hint):
            return [RawPlace(
                place_id='dia',
                name='Detroit Institute of Arts',
                formatted_address='5200 Woodward Ave, Detroit, MI',
                latitude=42.3594,
                longitude=-83.0646,
                primary_type='museum',
                types=['museum'],
                provider='fixture',
                provider_place_id='dia',
            )]

    monkeypatch.setattr(main, 'extractor', Extractor())
    monkeypatch.setattr(main, 'place_search', Search())

    response = client.post('/api/memories/ingest', json={
        'source_type': 'note',
        'source_text': 'saw Detroit Institute of Arts in a weekend guide',
    })

    assert response.status_code == 200
    body = response.json()
    assert body['memory']['resolution_status'] == 'resolved'
    assert body['memory']['hint']['name'] == 'Detroit Institute of Arts'
    assert body['memory']['place']['provider'] == 'fixture'
    assert client.get('/api/memories').json()[0]['place']['place_id'] == 'dia'


def test_image_ingest_runs_extraction_resolution_and_persistence(client, monkeypatch):
    from app.clients.google_maps import RawPlace
    from app.models import PlaceHint

    class Extractor:
        async def extract_image(self, data, mime_type, source_url=None):
            assert data == b'fake-png-bytes'
            assert mime_type == 'image/png'
            return PlaceHint(
                name='Detroit Institute of Arts',
                city_hint='Detroit',
                category_hint='museum',
                evidence='museum name visible in screenshot',
            )

    class Search:
        enabled = True

        async def search_places(self, hint):
            return [RawPlace(
                place_id='dia',
                name='Detroit Institute of Arts',
                formatted_address='5200 Woodward Ave, Detroit, MI',
                latitude=42.3594,
                longitude=-83.0646,
                primary_type='museum',
                types=['museum'],
                provider='fixture',
                provider_place_id='dia',
            )]

    monkeypatch.setattr(main, 'extractor', Extractor())
    monkeypatch.setattr(main, 'place_search', Search())

    response = client.post(
        '/api/memories/ingest-image',
        files={'image': ('save.png', b'fake-png-bytes', 'image/png')},
    )

    assert response.status_code == 200
    body = response.json()
    assert body['memory']['source_type'] == 'screenshot'
    assert body['memory']['resolution_status'] == 'resolved'
    assert body['memory']['source_text'] == 'museum name visible in screenshot'
    assert body['memory']['place']['provider_place_id'] == 'dia'
