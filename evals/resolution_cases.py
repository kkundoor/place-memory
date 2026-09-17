from dataclasses import dataclass

from app.clients.google_maps import RawPlace
from app.models import PlaceHint


@dataclass(frozen=True)
class LabeledCase:
    name: str
    hint: PlaceHint
    candidates: list[RawPlace]
    expected_id: str | None
    should_auto_resolve: bool


def place(
    place_id: str,
    name: str,
    address: str,
    category: str,
    latitude: float = 40.0,
    longitude: float = -73.0,
) -> RawPlace:
    return RawPlace(
        place_id=place_id,
        name=name,
        formatted_address=address,
        latitude=latitude,
        longitude=longitude,
        primary_type=category,
        types=[category],
        provider='fixture',
        provider_place_id=place_id,
    )


CASES = [
    LabeledCase(
        'exact business with city and category',
        PlaceHint(name="Carissa's Bakery", city_hint='East Hampton', category_hint='bakery'),
        [
            place('carissa', "Carissa's Bakery", 'East Hampton, NY', 'bakery'),
            place('carissa-ct', "Carissa's Bakery", 'New Haven, CT', 'bakery'),
        ],
        'carissa',
        True,
    ),
    LabeledCase(
        'minor typo with strong location',
        PlaceHint(name='Carisas Bakery', city_hint='East Hampton', category_hint='bakery'),
        [
            place('carissa', "Carissa's Bakery", 'East Hampton, NY', 'bakery'),
            place('carissa-ct', "Carissa's Bakery", 'New Haven, CT', 'bakery'),
        ],
        'carissa',
        True,
    ),
    LabeledCase(
        'ambiguous same-prefix venues',
        PlaceHint(name='The Point', city_hint='Southampton'),
        [
            place('point-bar', 'The Point Bar', 'Southampton, NY', 'bar'),
            place('point-cafe', 'The Point Cafe', 'Southampton, NY', 'cafe'),
        ],
        None,
        False,
    ),
    LabeledCase(
        'chain name without branch evidence',
        PlaceHint(name='Starbucks', category_hint='coffee shop'),
        [
            place('sb-1', 'Starbucks', '200 Main St, Ann Arbor, MI', 'coffee_shop'),
            place('sb-2', 'Starbucks', '300 State St, Ann Arbor, MI', 'coffee_shop'),
        ],
        None,
        False,
    ),
    LabeledCase(
        'chain disambiguated by address',
        PlaceHint(name='Starbucks', address_hint='300 State St', city_hint='Ann Arbor', category_hint='coffee shop'),
        [
            place('sb-1', 'Starbucks', '200 Main St, Ann Arbor, MI', 'coffee_shop'),
            place('sb-2', 'Starbucks', '300 State St, Ann Arbor, MI', 'coffee_shop'),
        ],
        'sb-2',
        True,
    ),
    LabeledCase(
        'wrong category should not be blindly trusted',
        PlaceHint(name='The Commons', city_hint='Detroit', category_hint='restaurant'),
        [
            place('commons-office', 'The Commons', 'Detroit, MI', 'office'),
            place('commons-restaurant', 'The Commons Kitchen', 'Detroit, MI', 'restaurant'),
        ],
        'commons-restaurant',
        False,
    ),
    LabeledCase(
        'no candidates',
        PlaceHint(name='Unknown Local Spot', city_hint='Detroit'),
        [],
        None,
        False,
    ),
    LabeledCase(
        'exact museum with full city',
        PlaceHint(name='Detroit Institute of Arts', city_hint='Detroit', category_hint='museum'),
        [
            place('dia', 'Detroit Institute of Arts', '5200 Woodward Ave, Detroit, MI', 'museum'),
            place('dia-shop', 'DIA Shop', '5200 Woodward Ave, Detroit, MI', 'store'),
        ],
        'dia',
        True,
    ),
    LabeledCase(
        'abbreviated name supported by city',
        PlaceHint(name='DIA', city_hint='Detroit', category_hint='museum'),
        [
            place('dia', 'Detroit Institute of Arts', '5200 Woodward Ave, Detroit, MI', 'museum'),
            place('dia-shop', 'DIA Shop', '5200 Woodward Ave, Detroit, MI', 'store'),
        ],
        'dia',
        False,
    ),
    LabeledCase(
        'same name different cities',
        PlaceHint(name='Union Coffee', city_hint='Detroit', category_hint='cafe'),
        [
            place('union-detroit', 'Union Coffee', 'Detroit, MI', 'cafe'),
            place('union-chicago', 'Union Coffee', 'Chicago, IL', 'cafe'),
        ],
        'union-detroit',
        True,
    ),
    LabeledCase(
        'category-only ambiguity',
        PlaceHint(name='Central Cafe', category_hint='cafe'),
        [
            place('central-1', 'Central Cafe', 'Royal Oak, MI', 'cafe'),
            place('central-2', 'Central Cafe', 'Detroit, MI', 'cafe'),
        ],
        None,
        False,
    ),
    LabeledCase(
        'address beats near-identical name',
        PlaceHint(name='Savas', address_hint='216 S State St', city_hint='Ann Arbor', category_hint='restaurant'),
        [
            place('savas', "Sava's", '216 S State St, Ann Arbor, MI', 'restaurant'),
            place('savas-market', "Sava's Market", '305 S Main St, Ann Arbor, MI', 'grocery_store'),
        ],
        'savas',
        True,
    ),
]
