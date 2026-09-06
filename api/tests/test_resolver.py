from app.clients.google_maps import RawPlace
from app.models import PlaceHint
from app.services.resolver import score_candidate


def test_exact_name_and_city_scores_high():
    hint = PlaceHint(name='Carissa’s Bakery', city_hint='East Hampton', category_hint='bakery')
    place = RawPlace(
        place_id='p1',
        name='Carissa’s Bakery',
        formatted_address='East Hampton, NY',
        latitude=40.96,
        longitude=-72.18,
        primary_type='bakery',
        types=['bakery', 'food'],
    )

    scored = score_candidate(hint, place)

    assert scored.confidence > 0.85


def test_wrong_name_does_not_get_false_confidence():
    hint = PlaceHint(name='Carissa’s Bakery', city_hint='East Hampton', category_hint='bakery')
    place = RawPlace(
        place_id='p2',
        name='East Hampton Grill',
        formatted_address='East Hampton, NY',
        latitude=40.96,
        longitude=-72.18,
        primary_type='restaurant',
        types=['restaurant', 'food'],
    )

    scored = score_candidate(hint, place)

    assert scored.confidence < 0.76
