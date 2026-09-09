from dataclasses import dataclass

from app.clients.google_maps import RawPlace
from app.models import PlaceHint, ResolutionStatus
from app.services.resolver import decide_resolution, score_candidate


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
        status, selected = decide_resolution(ranked)
        predicted_id = selected.place_id if status == ResolutionStatus.resolved and selected else None

        if predicted_id == case.expected_id:
            top1 += 1
        elif status == ResolutionStatus.resolved:
            false_confident += 1
        if status != ResolutionStatus.resolved:
            reviewed += 1

    total = max(1, len(cases))
    return {
        'top1_accuracy': top1 / total,
        'false_confident_rate': false_confident / total,
        'review_rate': reviewed / total,
    }
