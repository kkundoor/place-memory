from app.storage.assets import LocalAssetStore


def test_local_asset_store_survives_new_instance_and_deletes(tmp_path):
    root = tmp_path / 'uploads'
    first = LocalAssetStore(str(root))

    key = first.save('memory-1', b'original-image', 'image/png')

    second = LocalAssetStore(str(root))
    assert second.read(key) == b'original-image'

    second.delete(key)
    assert not (root / key).exists()


def test_local_asset_store_rejects_arbitrary_keys(tmp_path):
    store = LocalAssetStore(str(tmp_path / 'uploads'))

    try:
        store.read('../outside.png')
    except ValueError:
        pass
    else:
        raise AssertionError('path traversal key should be rejected')
