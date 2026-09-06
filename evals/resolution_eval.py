from dataclasses import dataclass

from app.clients.google_maps import RawPlace
from app.models import PlaceHint
from app.services.resolver import RESOLVE_THRESHOLD, score_candidate


@dataclass
class Case:
    hint: PlaceHint
    candidates: list[RawPlace]
    expected_id: str | None


def run(cases: list[Case]) -> dict[str, float]:
    top1 = 0
    false_confident = 0
    reviewed = 0

    for case in cases:
        ranked = sorted(
            [score_candidate(case.hint, item) for item in case.candidates],
            key=lambda item: item.confidence,
            reverse=True,
        )
        top = ranked[0] if ranked else None
        predicted_id = top.place_id if top else None
        confident = bool(top and top.confidence >= RESOLVE_THRESHOLD)

        if predicted_id == case.expected_id:
            top1 += 1
        elif confident:
            false_confident += 1
        if not confident:
            reviewed += 1

    total = max(1, len(cases))
    return {
        'top1_accuracy': top1 / total,
        'false_confident_rate': false_confident / total,
        'review_rate': reviewed / total,
    }
