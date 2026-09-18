from pathlib import Path
from typing import Protocol


_EXTENSIONS = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
}


class AssetStore(Protocol):
    def save(self, memory_id: str, data: bytes, mime_type: str) -> str: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class LocalAssetStore:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, memory_id: str, data: bytes, mime_type: str) -> str:
        extension = _EXTENSIONS.get(mime_type)
        if not extension:
            raise ValueError('unsupported asset media type')

        key = f'{memory_id}.{extension}'
        self._path(key).write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def _path(self, key: str) -> Path:
        if not key or Path(key).name != key:
            raise ValueError('invalid asset key')
        return self.root / key
