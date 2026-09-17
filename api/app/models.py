from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    note = 'note'
    screenshot = 'screenshot'
    link = 'link'


class ResolutionStatus(str, Enum):
    unresolved = 'unresolved'
    resolved = 'resolved'
    needs_review = 'needs_review'


class PlaceHint(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    city_hint: str | None = Field(default=None, max_length=120)
    address_hint: str | None = Field(default=None, max_length=300)
    category_hint: str | None = Field(default=None, max_length=100)
    evidence: str | None = Field(default=None, max_length=1500)


class PlaceCandidate(BaseModel):
    place_id: str = Field(min_length=1, max_length=300)
    provider: str = Field(default='unknown', min_length=1, max_length=80)
    provider_place_id: str | None = Field(default=None, max_length=300)
    name: str = Field(min_length=1, max_length=300)
    formatted_address: str | None = Field(default=None, max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    primary_type: str | None = Field(default=None, max_length=150)
    types: list[str] = Field(default_factory=list, max_length=50)
    confidence: float = Field(ge=0, le=1)
    confidence_reasons: list[str] = Field(default_factory=list)


class MemoryCreate(BaseModel):
    source_type: SourceType = SourceType.note
    source_text: str = Field(min_length=1, max_length=5000)
    source_url: HttpUrl | None = None
    note: str | None = Field(default=None, max_length=1000)
    hint: PlaceHint | None = None


class Memory(BaseModel):
    id: str
    source_type: SourceType
    source_text: str
    source_url: str | None = None
    note: str | None = None
    created_at: datetime
    resolution_status: ResolutionStatus
    hint: PlaceHint | None = None
    place: PlaceCandidate | None = None
    candidates: list[PlaceCandidate] = Field(default_factory=list)


class Origin(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class FeasibilityRequest(BaseModel):
    origin: Origin
    available_minutes: int = Field(default=120, ge=15, le=720)
    query: str = Field(default='', max_length=500)
    visit_minutes: int = Field(default=45, ge=0, le=360)


class FeasibleMemory(BaseModel):
    memory: Memory
    status: Literal['yes', 'no', 'uncertain']
    travel_minutes: int | None = None
    distance_meters: int | None = None
    open_now: bool | None = None
    reasons: list[str] = Field(default_factory=list)


class FeasibilityResponse(BaseModel):
    results: list[FeasibleMemory]
