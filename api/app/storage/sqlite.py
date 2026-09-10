from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.models import Memory, MemoryCreate, PlaceCandidate, PlaceHint, ResolutionStatus, SourceType


class MemoryStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                create table if not exists memories (
                    id text primary key,
                    source_type text not null,
                    source_text text not null,
                    source_url text,
                    note text,
                    created_at text not null,
                    resolution_status text not null,
                    hint_json text,
                    place_json text,
                    candidates_json text
                )
                '''
            )
            columns = {row['name'] for row in conn.execute('pragma table_info(memories)').fetchall()}
            if 'candidates_json' not in columns:
                conn.execute('alter table memories add column candidates_json text')

    def create(self, data: MemoryCreate) -> Memory:
        memory = Memory(
            id=str(uuid4()),
            source_type=data.source_type,
            source_text=data.source_text,
            source_url=str(data.source_url) if data.source_url else None,
            note=data.note,
            created_at=datetime.now(timezone.utc),
            resolution_status=ResolutionStatus.unresolved,
            hint=data.hint,
        )
        self._write(memory)
        return memory

    def list(self) -> list[Memory]:
        with self._connect() as conn:
            rows = conn.execute('select * from memories order by created_at desc').fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, memory_id: str) -> Memory | None:
        with self._connect() as conn:
            row = conn.execute('select * from memories where id = ?', (memory_id,)).fetchone()
        return self._from_row(row) if row else None

    def delete(self, memory_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute('delete from memories where id = ?', (memory_id,))
        return cursor.rowcount > 0

    def update_resolution(
        self,
        memory_id: str,
        hint: PlaceHint,
        place: PlaceCandidate | None,
        status: ResolutionStatus,
        candidates: list[PlaceCandidate] | None = None,
    ) -> Memory | None:
        memory = self.get(memory_id)
        if not memory:
            return None
        updated = memory.model_copy(update={
            'hint': hint,
            'place': place,
            'resolution_status': status,
            'candidates': memory.candidates if candidates is None else candidates,
        })
        self._write(updated)
        return updated

    def _write(self, memory: Memory) -> None:
        hint_json = memory.hint.model_dump_json() if memory.hint else None
        place_json = memory.place.model_dump_json() if memory.place else None
        candidates_json = json.dumps([item.model_dump() for item in memory.candidates])
        with self._connect() as conn:
            conn.execute(
                '''
                insert or replace into memories (
                    id, source_type, source_text, source_url, note, created_at,
                    resolution_status, hint_json, place_json, candidates_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    memory.id,
                    memory.source_type.value,
                    memory.source_text,
                    memory.source_url,
                    memory.note,
                    memory.created_at.isoformat(),
                    memory.resolution_status.value,
                    hint_json,
                    place_json,
                    candidates_json,
                ),
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Memory:
        hint = PlaceHint.model_validate_json(row['hint_json']) if row['hint_json'] else None
        place = PlaceCandidate.model_validate_json(row['place_json']) if row['place_json'] else None
        candidates = [
            PlaceCandidate.model_validate(item)
            for item in json.loads(row['candidates_json'] or '[]')
        ]
        return Memory(
            id=row['id'],
            source_type=SourceType(row['source_type']),
            source_text=row['source_text'],
            source_url=row['source_url'],
            note=row['note'],
            created_at=datetime.fromisoformat(row['created_at']),
            resolution_status=ResolutionStatus(row['resolution_status']),
            hint=hint,
            place=place,
            candidates=candidates,
        )
