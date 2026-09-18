from dataclasses import dataclass

from app.clients.google_maps import RawPlace
from app.models import PlaceHint


@dataclass(frozen=True)
class FieldCase:
    name: str
    hint: PlaceHint
    candidates: list[RawPlace]
    expected_mode: str
    expected_top_ids: set[str]


def place(
    place_id: str,
    name: str,
    address: str,
    latitude: float,
    longitude: float,
    primary_type: str,
    types: list[str],
) -> RawPlace:
    return RawPlace(
        place_id=place_id,
        name=name,
        formatted_address=address,
        latitude=latitude,
        longitude=longitude,
        primary_type=primary_type,
        types=types,
        provider='photon',
        provider_place_id=place_id.removeprefix('photon:'),
    )


CASES = [
    FieldCase(
        name='zingermans typo with city',
        hint=PlaceHint(
            name='Zingermans Delicatessen',
            city_hint='Ann Arbor',
            category_hint='delicatessen',
        ),
        candidates=[
            place('photon:N:12552300476', "Zingerman's Deli", '422 Detroit Street, Ann Arbor, Michigan, 48104, United States', 42.2846981, -83.7451513, 'restaurant', ['amenity', 'restaurant']),
            place('photon:N:4026754149', "Zingerman's Creamery", '3723 Plaza Drive, Ann Arbor, MI, 48108, United States', 42.2325862, -83.7480719, 'dairy', ['shop', 'dairy']),
            place('photon:N:4029305342', "Zingerman's Coffee Company", '3723 Plaza Drive, Ann Arbor, MI, 48108, United States', 42.2324263, -83.7483049, 'cafe', ['amenity', 'cafe']),
            place('photon:W:404262092', "Zingerman's Roadhouse", '2501 Jackson Avenue, Ann Arbor, Michigan, 48103, United States', 42.2800226, -83.7810408, 'restaurant', ['amenity', 'restaurant']),
            place('photon:N:12552300477', "Zingerman's Next Door Café", '418 Detroit Street, Ann Arbor, Michigan, 48104, United States', 42.28455, -83.7452712, 'cafe', ['amenity', 'cafe']),
        ],
        expected_mode='review',
        expected_top_ids={'photon:N:12552300476'},
    ),
    FieldCase(
        name='starbucks branch ambiguity',
        hint=PlaceHint(name='Starbucks', city_hint='Ann Arbor'),
        candidates=[
            place('photon:N:2742714779', 'Starbucks', '222 South State, Ann Arbor, MI, 48104, United States', 42.2794747, -83.7409739, 'cafe', ['amenity', 'cafe']),
            place('photon:N:9547980222', 'Starbucks', '2000 West Waters Road, Ann Arbor, MI, 48103, United States', 42.2436499, -83.7696695, 'cafe', ['amenity', 'cafe']),
            place('photon:W:93681661', 'Starbucks', '4585 Washtenaw Avenue, Ann Arbor, MI, 48108, United States', 42.2522924, -83.6691535, 'cafe', ['amenity', 'cafe']),
            place('photon:N:541900696', 'Starbucks', '3601 Washtenaw Avenue, Ann Arbor, MI, 48104, United States', 42.255706, -83.6880809, 'cafe', ['amenity', 'cafe']),
            place('photon:W:549854176', 'Starbucks', '3141 Ann Arbor-Saline Road, Ann Arbor, MI, 48103, United States', 42.2414024, -83.7680244, 'cafe', ['amenity', 'cafe']),
        ],
        expected_mode='review',
        expected_top_ids=set(),
    ),
    FieldCase(
        name='carissas provider miss returns geography',
        hint=PlaceHint(
            name="Carissa's Bakery",
            city_hint='East Hampton, New York',
            category_hint='bakery',
        ),
        candidates=[
            place('photon:R:175730', 'East Hampton North', 'East Hampton, New York, United States', 40.9745288, -72.1747867, 'census', ['boundary', 'census']),
            place('photon:R:175509', 'East Hampton', 'East Hampton, New York, United States', 40.9633868, -72.1847598, 'town', ['place', 'town']),
            place('photon:N:8942982893', 'East Hampton North', 'East Hampton, New York, 11937, United States', 40.9724872, -72.1887727, 'village', ['place', 'village']),
            place('photon:N:7091232853', 'East Hampton', 'Railroad Avenue, East Hampton, New York, 11937, United States', 40.9650535, -72.1935105, 'station', ['railway', 'station']),
            place('photon:R:14355603', 'East Hampton', 'New York, United States', 40.9633868, -72.1847598, 'town', ['place', 'town']),
        ],
        expected_mode='abstain',
        expected_top_ids=set(),
    ),
    FieldCase(
        name='dia duplicate osm representations',
        hint=PlaceHint(name='Detroit Institute of Arts', city_hint='Detroit'),
        candidates=[
            place('photon:N:10905214429', 'Detroit Institute of Arts', 'John R Street, Detroit, Michigan, 48203, United States', 42.3595402, -83.0641933, 'arts_centre', ['amenity', 'arts_centre']),
            place('photon:R:1553447', 'Detroit Institute of Arts', '5200 Woodward Avenue, Detroit, MI, 48202, United States', 42.3595055, -83.0645225, 'museum', ['tourism', 'museum']),
            place('photon:W:666800537', 'Institute of Martial Arts', '16849 West Warren Avenue, Detroit, MI, 48239, United States', 42.3432216, -83.2108339, 'dojo', ['amenity', 'dojo']),
        ],
        expected_mode='auto',
        expected_top_ids={'photon:N:10905214429', 'photon:R:1553447'},
    ),
    FieldCase(
        name='generic coffee shop has no identity',
        hint=PlaceHint(name='Coffee Shop', category_hint='coffee shop'),
        candidates=[
            place('photon:W:19521588', 'Coffee Shop Road', 'Ripley, Tennessee, 38063, United States', 35.7789777, -89.5324087, 'unclassified', ['highway', 'unclassified']),
            place('photon:W:19521581', 'Coffee Shop Road', 'Tennessee, 38063, United States', 35.776206, -89.4997231, 'residential', ['highway', 'residential']),
            place('photon:W:420324669', "Pann's Coffee Shop", '6710 South La Tijera Boulevard, Los Angeles, CA, 90045, United States', 33.9781387, -118.3705651, 'restaurant', ['amenity', 'restaurant']),
            place('photon:W:426020566', "Johnie's Coffee Shop", '6101 Wilshire Boulevard, Los Angeles, CA, 90036, United States', 34.0633135, -118.3616337, 'commercial', ['building', 'commercial']),
            place('photon:W:1456153364', 'Coffee Shop La Tienda de los Mecatos', 'Quindío, Colombia', 4.4902919, -75.7402169, 'industrial', ['landuse', 'industrial']),
        ],
        expected_mode='abstain',
        expected_top_ids=set(),
    ),
]
