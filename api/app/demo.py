from datetime import datetime, timezone

from app.clients.google_maps import RawPlace
from app.models import (
    Memory,
    PlaceHint,
    ResolutionMethod,
    ResolutionStatus,
    SourceType,
)
from app.services.resolver import resolution_metrics, resolve_hint


DEMO_TIME = datetime(2026, 9, 17, tzinfo=timezone.utc)


class DemoSearch:
    def __init__(self, places: list[RawPlace]):
        self.places = places

    async def search_places(self, hint: PlaceHint) -> list[RawPlace]:
        return self.places


def place(
    place_id: str,
    name: str,
    address: str,
    latitude: float,
    longitude: float,
    primary_type: str,
    types: list[str],
    aliases: list[str] | None = None,
) -> RawPlace:
    return RawPlace(
        place_id=place_id,
        name=name,
        aliases=aliases or [],
        formatted_address=address,
        latitude=latitude,
        longitude=longitude,
        primary_type=primary_type,
        types=types,
        provider="photon",
        provider_place_id=place_id.removeprefix("photon:"),
    )


async def build_sample(
    *,
    sample_id: str,
    source_type: SourceType,
    source_text: str,
    note: str,
    hint: PlaceHint,
    raw_candidates: list[RawPlace],
) -> Memory:
    status, selected, ranked = await resolve_hint(hint, DemoSearch(raw_candidates))
    confidence, gap = resolution_metrics(ranked)

    method = (
        ResolutionMethod.auto
        if status == ResolutionStatus.resolved
        else ResolutionMethod.abstained
        if status == ResolutionStatus.unresolved
        else None
    )

    return Memory(
        id=sample_id,
        source_type=source_type,
        source_text=source_text,
        note=note,
        created_at=DEMO_TIME,
        resolution_status=status,
        resolution_method=method,
        pre_resolution_confidence=confidence,
        pre_resolution_gap=gap,
        hint=hint,
        place=selected if status == ResolutionStatus.resolved else None,
        candidates=ranked,
    )


async def demo_memories() -> list[Memory]:
    stow = await build_sample(
        sample_id="demo-stow-lake",
        source_type=SourceType.screenshot,
        source_text="STOW LAKE - San Francisco - pedal boat rental",
        note=(
            "Visible evidence in the original pilot included a STOW LAKE logo, "
            "a San Francisco location tag, and pedal-boat context."
        ),
        hint=PlaceHint(
            name="Stow Lake",
            city_hint="San Francisco",
            category_hint="lake",
            activity_hint="boat rental",
        ),
        raw_candidates=[
            place(
                "photon:R:12908",
                "Blue Heron Lake",
                "San Francisco, California, United States",
                37.7689904,
                -122.4728548,
                "lake",
                ["water", "lake"],
                aliases=["Stow Lake"],
            ),
            place(
                "photon:W:673500610",
                "Blue Heron Lake Drive",
                "San Francisco, California, 94122, United States",
                37.7710724,
                -122.4750211,
                "pedestrian",
                ["highway", "pedestrian"],
            ),
            place(
                "photon:W:120479803",
                "Blue Heron Lake Boathouse & Bike Rental",
                "Blue Heron Lake Drive, San Francisco, California, 94122, United States",
                37.7706117,
                -122.4771078,
                "boat_rental",
                ["amenity", "boat_rental"],
            ),
        ],
    )

    zingermans = await build_sample(
        sample_id="demo-zingermans",
        source_type=SourceType.note,
        source_text=(
            "Zingermans Delicatessen in Ann Arbor - "
            "want to go here for sandwiches sometime"
        ),
        note=(
            "The Deli ranks first, but another Zingerman's location is close "
            "enough that the resolver asks for confirmation instead of guessing."
        ),
        hint=PlaceHint(
            name="Zingermans Delicatessen",
            city_hint="Ann Arbor",
            category_hint="delicatessen",
        ),
        raw_candidates=[
            place(
                "photon:N:12552300476",
                "Zingerman's Deli",
                "422 Detroit Street, Ann Arbor, Michigan, 48104, United States",
                42.2846981,
                -83.7451513,
                "restaurant",
                ["amenity", "restaurant"],
            ),
            place(
                "photon:N:4026754149",
                "Zingerman's Creamery",
                "3723 Plaza Drive, Ann Arbor, MI, 48108, United States",
                42.2325862,
                -83.7480719,
                "dairy",
                ["shop", "dairy"],
            ),
            place(
                "photon:N:4029305342",
                "Zingerman's Coffee Company",
                "3723 Plaza Drive, Ann Arbor, MI, 48108, United States",
                42.2324263,
                -83.7483049,
                "cafe",
                ["amenity", "cafe"],
            ),
            place(
                "photon:W:404262092",
                "Zingerman's Roadhouse",
                "2501 Jackson Avenue, Ann Arbor, Michigan, 48103, United States",
                42.2800226,
                -83.7810408,
                "restaurant",
                ["amenity", "restaurant"],
            ),
            place(
                "photon:N:12552300477",
                "Zingerman's Next Door Cafe",
                "418 Detroit Street, Ann Arbor, Michigan, 48104, United States",
                42.28455,
                -83.7452712,
                "cafe",
                ["amenity", "cafe"],
            ),
        ],
    )

    generic = await build_sample(
        sample_id="demo-generic-coffee",
        source_type=SourceType.note,
        source_text="this coffee shop",
        note=(
            "There is no actual business identity here, so the correct behavior "
            "is to abstain rather than turn a generic category into a place."
        ),
        hint=PlaceHint(
            name="Coffee Shop",
            category_hint="coffee shop",
        ),
        raw_candidates=[
            place(
                "photon:W:19521588",
                "Coffee Shop Road",
                "Ripley, Tennessee, 38063, United States",
                35.7789777,
                -89.5324087,
                "unclassified",
                ["highway", "unclassified"],
            ),
            place(
                "photon:W:19521581",
                "Coffee Shop Road",
                "Tennessee, 38063, United States",
                35.776206,
                -89.4997231,
                "residential",
                ["highway", "residential"],
            ),
            place(
                "photon:W:420324669",
                "Pann's Coffee Shop",
                "6710 South La Tijera Boulevard, Los Angeles, CA, 90045, United States",
                33.9781387,
                -118.3705651,
                "restaurant",
                ["amenity", "restaurant"],
            ),
        ],
    )

    return [stow, zingermans, generic]
