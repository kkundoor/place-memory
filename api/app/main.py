import base64
import logging
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.clients.enriched import AliasEnrichedPlaceSearchClient
from app.clients.gemini import GeminiExtractor
from app.clients.google_maps import GoogleMapsClient
from app.clients.nominatim import NominatimClient
from app.clients.photon import PhotonClient
from app.config import get_settings
from app.demo import demo_memories
from app.models import (
    FeasibilityRequest,
    FeasibilityResponse,
    Memory,
    MemoryCreate,
    PlaceCandidate,
    PlaceHint,
    ResolutionMethod,
    ResolutionStatus,
    SourceType,
)
from app.services.feasibility import check_memories
from app.services.resolver import explain_resolution, resolution_metrics, resolve_hint
from app.services.retrieval import search_memories
from app.storage.assets import LocalAssetStore
from app.storage.sqlite import MemoryStore


logger = logging.getLogger('place_memory.api')

settings = get_settings()
store = MemoryStore(settings.database_path)
asset_store = LocalAssetStore(settings.upload_dir)
maps = GoogleMapsClient(settings.google_maps_api_key)
photon = PhotonClient(settings.photon_base_url, settings.photon_user_agent)
nominatim = NominatimClient(settings.nominatim_base_url, settings.nominatim_user_agent)
photon_with_aliases = AliasEnrichedPlaceSearchClient(photon, nominatim)
place_search = maps if maps.enabled else photon_with_aliases if photon.enabled else nominatim
extractor = GeminiExtractor(settings)

app = FastAPI(title='place memory api', version='0.4.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def demo_read_only(request, call_next):
    if (
        settings.app_env == 'demo'
        and request.url.path.startswith('/api/')
        and not request.url.path.startswith('/api/demo/')
        and request.method not in {'GET', 'HEAD', 'OPTIONS'}
    ):
        return JSONResponse(
            status_code=403,
            content={'detail': 'public demo does not persist visitor data'},
        )
    return await call_next(request)


@app.middleware('http')
async def request_metadata(request, call_next):
    request_id = request.headers.get('x-request-id') or str(uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers['x-request-id'] = request_id
    logger.info(
        'request_complete request_id=%s method=%s path=%s status=%s duration_ms=%s',
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get('/health')
def health() -> dict:
    return {
        'status': 'ok',
        'app_env': settings.app_env,
        'demo_mode': settings.app_env == 'demo',
        'place_search_enabled': place_search.enabled,
        'place_search_provider': (
            'google' if maps.enabled
            else 'photon+nominatim-aliases' if photon.enabled and nominatim.enabled
            else 'photon' if photon.enabled
            else 'nominatim'
        ),
        'maps_enabled': maps.enabled,
        'gemini_enabled': extractor.enabled,
    }


@app.post('/api/memories', response_model=Memory)
def create_memory(data: MemoryCreate) -> Memory:
    return store.create(data)


@app.get('/api/memories', response_model=list[Memory])
async def list_memories(q: str = '') -> list[Memory]:
    memories = (
        await demo_memories()
        if settings.app_env == 'demo'
        else store.list()
    )
    return search_memories(memories, q) if q else memories


@app.get('/api/memories/{memory_id}/source-image')
def source_image(memory_id: str) -> Response:
    memory = store.get(memory_id)
    if not memory or not memory.source_asset_key or not memory.source_asset_mime_type:
        raise HTTPException(status_code=404, detail='source image not found')
    try:
        data = asset_store.read(memory.source_asset_key)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail='source image not found')
    return Response(content=data, media_type=memory.source_asset_mime_type)


@app.delete('/api/memories/{memory_id}', status_code=204)
def delete_memory(memory_id: str) -> Response:
    memory = store.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail='memory not found')

    if memory.source_asset_key:
        asset_store.delete(memory.source_asset_key)

    store.delete(memory_id)
    return Response(status_code=204)


def _persist_resolution(
    memory_id: str,
    hint: PlaceHint,
    status: ResolutionStatus,
    selected: PlaceCandidate | None,
    candidates: list[PlaceCandidate],
) -> Memory | None:
    confidence, gap = resolution_metrics(candidates)
    method = (
        ResolutionMethod.auto
        if status == ResolutionStatus.resolved
        else ResolutionMethod.abstained
        if status == ResolutionStatus.unresolved
        else None
    )
    canonical = selected if status == ResolutionStatus.resolved else None
    return store.update_resolution(
        memory_id,
        hint,
        canonical,
        status,
        candidates,
        resolution_method=method,
        pre_resolution_confidence=confidence,
        pre_resolution_gap=gap,
    )




DEMO_WINDOW_SECONDS = 60 * 60
DEMO_MAX_CALLS_PER_WINDOW = 60
_demo_call_times: deque[float] = deque()


def _consume_demo_budget() -> None:
    now = time.monotonic()
    cutoff = now - DEMO_WINDOW_SECONDS

    while _demo_call_times and _demo_call_times[0] <= cutoff:
        _demo_call_times.popleft()

    if len(_demo_call_times) >= DEMO_MAX_CALLS_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail='public demo is temporarily at capacity; try again later',
        )

    _demo_call_times.append(now)


async def _resolve_demo_hint(
    hint: PlaceHint,
    *,
    source_type: SourceType,
    source_text: str,
    source_url: str | None = None,
    note: str | None = None,
) -> dict:
    if not place_search.enabled:
        memory = Memory(
            id=f'demo-live-{uuid4()}',
            source_type=source_type,
            source_text=source_text,
            source_url=source_url,
            note=note,
            created_at=datetime.now(timezone.utc),
            resolution_status=ResolutionStatus.unresolved,
            resolution_method=ResolutionMethod.abstained,
            hint=hint,
            candidates=[],
        )
        return {
            'memory': memory,
            'candidates': [],
            'warning': 'place search is temporarily unavailable',
        }

    try:
        status, selected, candidates = await resolve_hint(hint, place_search)
    except httpx.HTTPError as exc:
        logger.exception('demo_place_search_failed')
        raise HTTPException(
            status_code=503,
            detail='place search is temporarily unavailable',
        ) from exc

    confidence, gap = resolution_metrics(candidates)

    method = (
        ResolutionMethod.auto
        if status == ResolutionStatus.resolved
        else ResolutionMethod.abstained
        if status == ResolutionStatus.unresolved
        else None
    )

    memory = Memory(
        id=f'demo-live-{uuid4()}',
        source_type=source_type,
        source_text=source_text,
        source_url=source_url,
        note=note,
        created_at=datetime.now(timezone.utc),
        resolution_status=status,
        resolution_method=method,
        pre_resolution_confidence=confidence,
        pre_resolution_gap=gap,
        hint=hint,
        place=selected if status == ResolutionStatus.resolved else None,
        candidates=candidates,
    )

    return {
        'memory': memory,
        'candidates': candidates,
    }


@app.post('/api/demo/resolve')
async def demo_resolve_text(data: MemoryCreate) -> dict:
    _consume_demo_budget()

    try:
        hint = data.hint or await extractor.extract_text(data.source_text)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return await _resolve_demo_hint(
        hint,
        source_type=data.source_type,
        source_text=data.source_text,
        source_url=str(data.source_url) if data.source_url else None,
        note=data.note,
    )


@app.post('/api/demo/resolve-image')
async def demo_resolve_image(
    image: UploadFile = File(...),
    source_url: str | None = Form(default=None),
    note: str | None = Form(default=None),
) -> dict:
    _consume_demo_budget()

    if image.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        raise HTTPException(status_code=415, detail='jpeg, png, or webp required')

    data = await image.read()

    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='image must be under 8 MB')

    context = note.strip() if note and note.strip() else None

    try:
        hint = await extractor.extract_image(
            data,
            image.content_type,
            source_url,
            context,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return await _resolve_demo_hint(
        hint,
        source_type=SourceType.screenshot,
        source_text=hint.evidence or hint.name or 'screenshot',
        source_url=source_url,
        note=context,
    )


@app.post('/api/memories/ingest')
async def ingest_memory(data: MemoryCreate) -> dict:
    try:
        hint = data.hint or await extractor.extract_text(data.source_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    memory = store.create(data.model_copy(update={'hint': hint}))
    if not place_search.enabled:
        updated = store.update_resolution(memory.id, hint, None, ResolutionStatus.unresolved)
        return {'memory': updated, 'candidates': [], 'warning': 'place search is not configured'}

    try:
        status, selected, candidates = await resolve_hint(hint, place_search)
    except httpx.HTTPError:
        logger.exception('place_search_failed memory_id=%s', memory.id)
        updated = store.update_resolution(memory.id, hint, None, ResolutionStatus.unresolved)
        return {'memory': updated, 'candidates': [], 'warning': 'place search is temporarily unavailable'}

    updated = _persist_resolution(memory.id, hint, status, selected, candidates)
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

    context = note.strip() if note and note.strip() else None

    try:
        if context:
            hint = await extractor.extract_image(data, image.content_type, source_url, context)
        else:
            hint = await extractor.extract_image(data, image.content_type, source_url)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    memory = store.create(MemoryCreate(
        source_type=SourceType.screenshot,
        source_text=hint.evidence or hint.name or 'screenshot',
        source_url=source_url,
        note=context,
        hint=hint,
    ))

    key = None
    try:
        key = asset_store.save(memory.id, data, image.content_type)
        attached = store.attach_asset(memory.id, key, image.content_type)
        if not attached:
            raise RuntimeError('memory disappeared before asset attachment')
        memory = attached
    except Exception as exc:
        if key:
            try:
                asset_store.delete(key)
            except Exception:
                logger.exception('asset_cleanup_failed memory_id=%s', memory.id)
        store.delete(memory.id)
        logger.exception('asset_persist_failed memory_id=%s', memory.id)
        raise HTTPException(status_code=500, detail='could not persist source image') from exc

    if not place_search.enabled:
        updated = store.update_resolution(memory.id, hint, None, ResolutionStatus.unresolved)
        return {'memory': updated, 'candidates': [], 'warning': 'place search is not configured'}

    try:
        status, selected, candidates = await resolve_hint(hint, place_search)
    except httpx.HTTPError:
        logger.exception('place_search_failed memory_id=%s', memory.id)
        updated = store.update_resolution(memory.id, hint, None, ResolutionStatus.unresolved)
        return {'memory': updated, 'candidates': [], 'warning': 'place search is temporarily unavailable'}

    updated = _persist_resolution(memory.id, hint, status, selected, candidates)
    return {'memory': updated, 'candidates': candidates}


@app.post('/api/memories/{memory_id}/resolve')
async def resolve_memory(memory_id: str, hint: PlaceHint) -> dict:
    if not store.get(memory_id):
        raise HTTPException(status_code=404, detail='memory not found')
    if not place_search.enabled:
        raise HTTPException(status_code=503, detail='place search is not configured')

    try:
        status, selected, candidates = await resolve_hint(hint, place_search)
    except httpx.HTTPError as exc:
        logger.exception('place_search_failed memory_id=%s', memory_id)
        raise HTTPException(status_code=503, detail='place search is temporarily unavailable') from exc
    memory = _persist_resolution(memory_id, hint, status, selected, candidates)
    return {'memory': memory, 'candidates': candidates}


@app.get('/api/memories/{memory_id}/resolution')
def resolution_explanation(memory_id: str) -> dict:
    memory = store.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail='memory not found')
    return {
        'memory_id': memory.id,
        'hint': memory.hint.model_dump() if memory.hint else None,
        **explain_resolution(
            memory.resolution_status,
            memory.candidates,
            memory.resolution_method,
            memory.pre_resolution_confidence,
            memory.pre_resolution_gap,
        ),
    }


@app.post('/api/memories/{memory_id}/confirm', response_model=Memory)
def confirm_memory(memory_id: str, candidate: PlaceCandidate) -> Memory:
    memory = store.get(memory_id)
    if not memory or not memory.hint:
        raise HTTPException(status_code=404, detail='memory or hint not found')

    if memory.candidates:
        selected = next(
            (item for item in memory.candidates if item.place_id == candidate.place_id),
            None,
        )
        if not selected:
            raise HTTPException(status_code=400, detail='candidate was not offered for review')
    elif settings.app_env == 'local':
        selected = candidate
    else:
        raise HTTPException(status_code=409, detail='no stored candidates available for confirmation')

    updated = store.update_resolution(
        memory_id,
        memory.hint,
        selected.model_copy(update={
            'confidence_reasons': [*selected.confidence_reasons, 'confirmed by user'],
        }),
        ResolutionStatus.resolved,
        memory.candidates,
        resolution_method=ResolutionMethod.manual,
        pre_resolution_confidence=(
            memory.pre_resolution_confidence
            if memory.pre_resolution_confidence is not None
            else selected.confidence
        ),
        pre_resolution_gap=memory.pre_resolution_gap,
    )
    if not updated:
        raise HTTPException(status_code=404, detail='memory not found')
    return updated


@app.post('/api/memories/{memory_id}/reject', response_model=Memory)
def reject_memory_candidates(memory_id: str) -> Memory:
    memory = store.get(memory_id)
    if not memory or not memory.hint:
        raise HTTPException(status_code=404, detail='memory or hint not found')

    updated = store.update_resolution(
        memory_id,
        memory.hint,
        None,
        ResolutionStatus.unresolved,
        memory.candidates,
        resolution_method=ResolutionMethod.abstained,
        pre_resolution_confidence=memory.pre_resolution_confidence,
        pre_resolution_gap=memory.pre_resolution_gap,
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


static_dir = Path(settings.static_dir) if settings.static_dir else None
if static_dir and static_dir.exists():
    app.mount('/', StaticFiles(directory=str(static_dir), html=True), name='web')
