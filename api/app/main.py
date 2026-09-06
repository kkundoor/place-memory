from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.clients.google_maps import GoogleMapsClient
from app.config import get_settings
from app.models import (
    FeasibilityRequest,
    FeasibilityResponse,
    Memory,
    MemoryCreate,
    PlaceCandidate,
    PlaceHint,
    ResolutionStatus,
)
from app.services.feasibility import check_memory
from app.services.resolver import resolve_hint
from app.services.retrieval import search_memories
from app.storage.sqlite import MemoryStore


settings = get_settings()
store = MemoryStore(settings.database_path)
maps = GoogleMapsClient(settings.google_maps_api_key)

app = FastAPI(title='place memory api', version='0.1.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health() -> dict:
    return {
        'status': 'ok',
        'maps_enabled': maps.enabled,
    }


@app.post('/api/memories', response_model=Memory)
def create_memory(data: MemoryCreate) -> Memory:
    return store.create(data)


@app.get('/api/memories', response_model=list[Memory])
def list_memories(q: str = '') -> list[Memory]:
    memories = store.list()
    return search_memories(memories, q) if q else memories


@app.post('/api/memories/{memory_id}/resolve')
async def resolve_memory(memory_id: str, hint: PlaceHint) -> dict:
    if not store.get(memory_id):
        raise HTTPException(status_code=404, detail='memory not found')
    if not maps.enabled:
        raise HTTPException(status_code=503, detail='google maps is not configured')

    status, selected, candidates = await resolve_hint(hint, maps)
    memory = store.update_resolution(memory_id, hint, selected, status)
    return {
        'memory': memory,
        'candidates': candidates,
    }


@app.post('/api/memories/{memory_id}/confirm', response_model=Memory)
def confirm_memory(memory_id: str, candidate: PlaceCandidate) -> Memory:
    memory = store.get(memory_id)
    if not memory or not memory.hint:
        raise HTTPException(status_code=404, detail='memory or hint not found')
    updated = store.update_resolution(
        memory_id,
        memory.hint,
        candidate.model_copy(update={'confidence': 1.0}),
        ResolutionStatus.resolved,
    )
    if not updated:
        raise HTTPException(status_code=404, detail='memory not found')
    return updated


@app.post('/api/feasible', response_model=FeasibilityResponse)
async def feasible(data: FeasibilityRequest) -> FeasibilityResponse:
    memories = search_memories(store.list(), data.query)
    results = [
        await check_memory(memory, data.origin, data.available_minutes, data.visit_minutes, maps)
        for memory in memories
    ]
    order = {'yes': 0, 'uncertain': 1, 'no': 2}
    results.sort(key=lambda result: (
        order[result.status],
        result.travel_minutes if result.travel_minutes is not None else 10**9,
    ))
    return FeasibilityResponse(results=results)
