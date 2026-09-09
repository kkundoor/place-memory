import base64

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.clients.gemini import GeminiExtractor
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
    SourceType,
)
from app.services.feasibility import check_memories
from app.services.resolver import resolve_hint
from app.services.retrieval import search_memories
from app.storage.sqlite import MemoryStore


settings = get_settings()
store = MemoryStore(settings.database_path)
maps = GoogleMapsClient(settings.google_maps_api_key)
extractor = GeminiExtractor(settings)

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
        'vertex_enabled': extractor.enabled,
    }


@app.post('/api/memories', response_model=Memory)
def create_memory(data: MemoryCreate) -> Memory:
    return store.create(data)


@app.get('/api/memories', response_model=list[Memory])
def list_memories(q: str = '') -> list[Memory]:
    memories = store.list()
    return search_memories(memories, q) if q else memories


@app.post('/api/memories/ingest')
async def ingest_memory(data: MemoryCreate) -> dict:
    memory = store.create(data)
    hint = data.hint or await extractor.extract_text(data.source_text)
    if not maps.enabled:
        updated = store.update_resolution(memory.id, hint, None, ResolutionStatus.unresolved)
        return {'memory': updated, 'candidates': [], 'warning': 'google maps is not configured'}

    status, selected, candidates = await resolve_hint(hint, maps)
    updated = store.update_resolution(memory.id, hint, selected, status)
    return {'memory': updated, 'candidates': candidates}


@app.post('/api/memories/ingest-image')
async def ingest_image(
    image: UploadFile = File(...),
    source_url: str | None = Form(default=None),
    note: str | None = Form(default=None),
) -> dict:
    if image.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        raise HTTPException(status_code=415, detail='jpeg, png, or webp required')
    data = await image.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='image must be under 8 MB')

    try:
        hint = await extractor.extract_image(data, image.content_type, source_url)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    memory = store.create(MemoryCreate(
        source_type=SourceType.screenshot,
        source_text=hint.evidence or hint.name,
        source_url=source_url,
        note=note,
        hint=hint,
    ))
    if not maps.enabled:
        updated = store.update_resolution(memory.id, hint, None, ResolutionStatus.unresolved)
        return {'memory': updated, 'candidates': [], 'warning': 'google maps is not configured'}

    status, selected, candidates = await resolve_hint(hint, maps)
    updated = store.update_resolution(memory.id, hint, selected, status)
    return {'memory': updated, 'candidates': candidates}


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
    results = await check_memories(
        memories,
        data.origin,
        data.available_minutes,
        data.visit_minutes,
        maps,
    )
    return FeasibilityResponse(results=results)


@app.post('/api/map')
async def map_image(data: FeasibilityRequest) -> dict:
    memories = search_memories(store.list(), data.query)
    coordinates = [
        (memory.place.latitude, memory.place.longitude)
        for memory in memories
        if memory.place
    ]
    image = await maps.static_map(data.origin, coordinates)
    if image is None:
        raise HTTPException(status_code=503, detail='google maps is not configured')
    return {
        'image_base64': base64.b64encode(image).decode('ascii'),
        'count': len(coordinates),
    }
