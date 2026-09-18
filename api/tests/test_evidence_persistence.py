from fastapi.testclient import TestClient

from app import main
from app.models import MemoryCreate, PlaceHint
from app.storage.assets import LocalAssetStore
from app.storage.sqlite import MemoryStore


class DisabledPlaceSearch:
    enabled = False

    async def search_places(self, hint):
        return []


def build_client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'store', MemoryStore(str(tmp_path / 'test.db')))
    monkeypatch.setattr(main, 'asset_store', LocalAssetStore(str(tmp_path / 'uploads')))
    monkeypatch.setattr(main, 'place_search', DisabledPlaceSearch())
    return TestClient(main.app)


def test_image_ingest_persists_original_bytes_and_context(tmp_path, monkeypatch):
    class Extractor:
        async def extract_image(self, data, mime_type, source_url=None, context=None):
            assert data == b'fake-png'
            assert mime_type == 'image/png'
            assert source_url == 'https://example.com/post'
            assert context == 'friend said this was in Detroit'
            return PlaceHint(
                name='Detroit Institute of Arts',
                city_hint='Detroit',
                category_hint='museum',
                evidence='museum name visible in screenshot',
            )

    monkeypatch.setattr(main, 'extractor', Extractor())
    client = build_client(tmp_path, monkeypatch)

    response = client.post(
        '/api/memories/ingest-image',
        files={'image': ('save.png', b'fake-png', 'image/png')},
        data={
            'source_url': 'https://example.com/post',
            'note': 'friend said this was in Detroit',
        },
    )

    assert response.status_code == 200
    memory = response.json()['memory']
    assert memory['source_asset_key']
    assert memory['source_asset_mime_type'] == 'image/png'
    assert memory['note'] == 'friend said this was in Detroit'

    image = client.get(f"/api/memories/{memory['id']}/source-image")
    assert image.status_code == 200
    assert image.content == b'fake-png'
    assert image.headers['content-type'] == 'image/png'


def test_delete_memory_removes_source_asset(tmp_path, monkeypatch):
    class Extractor:
        async def extract_image(self, data, mime_type, source_url=None):
            return PlaceHint(name='Saved Place', evidence='saved place')

    monkeypatch.setattr(main, 'extractor', Extractor())
    client = build_client(tmp_path, monkeypatch)

    response = client.post(
        '/api/memories/ingest-image',
        files={'image': ('save.webp', b'fake-webp', 'image/webp')},
    )
    memory = response.json()['memory']
    asset_path = tmp_path / 'uploads' / memory['source_asset_key']
    assert asset_path.exists()

    deleted = client.delete(f"/api/memories/{memory['id']}")
    assert deleted.status_code == 204
    assert not asset_path.exists()
    assert client.get(f"/api/memories/{memory['id']}/source-image").status_code == 404


def test_extraction_failure_leaves_no_memory_or_asset(tmp_path, monkeypatch):
    class Extractor:
        async def extract_image(self, data, mime_type, source_url=None):
            raise RuntimeError('gemini request failed; retry shortly')

    monkeypatch.setattr(main, 'extractor', Extractor())
    client = build_client(tmp_path, monkeypatch)

    response = client.post(
        '/api/memories/ingest-image',
        files={'image': ('save.png', b'fake-png', 'image/png')},
    )

    assert response.status_code == 503
    assert client.get('/api/memories').json() == []
    assert list((tmp_path / 'uploads').iterdir()) == []


def test_old_screenshot_without_asset_returns_404(tmp_path, monkeypatch):
    client = build_client(tmp_path, monkeypatch)
    memory = main.store.create(MemoryCreate(
        source_type='screenshot',
        source_text='old screenshot row',
    ))

    response = client.get(f'/api/memories/{memory.id}/source-image')

    assert response.status_code == 404
