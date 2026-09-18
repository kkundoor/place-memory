import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'api'))

from app.models import ResolutionStatus  # noqa: E402
from app.services.resolver import resolve_hint  # noqa: E402
from resolution_cases import CASES  # noqa: E402


class Search:
    def __init__(self, places):
        self.places = places

    async def search_places(self, hint):
        return self.places


async def evaluate() -> dict:
    rows = []
    correct_top1 = truth_cases = correct_auto = auto_count = expected_auto = false_auto = review_count = 0
    for case in CASES:
        status, selected, ranked = await resolve_hint(case.hint, Search(case.candidates))
        top_id = ranked[0].place_id if ranked else None
        resolved_id = selected.place_id if status == ResolutionStatus.resolved and selected else None
        if case.expected_id is not None:
            truth_cases += 1
            correct_top1 += int(top_id == case.expected_id)
        if case.should_auto_resolve:
            expected_auto += 1
        if status == ResolutionStatus.resolved:
            auto_count += 1
            if resolved_id == case.expected_id and case.should_auto_resolve:
                correct_auto += 1
            else:
                false_auto += 1
        else:
            review_count += 1
        rows.append({
            'case': case.name,
            'expected_id': case.expected_id,
            'should_auto_resolve': case.should_auto_resolve,
            'status': status.value,
            'top_id': top_id,
            'top_confidence': ranked[0].confidence if ranked else None,
            'resolved_id': resolved_id,
        })
    total = len(CASES)
    return {
        'summary': {
            'cases': total,
            'top1_accuracy_on_labeled_cases': round(correct_top1 / max(1, truth_cases), 4),
            'auto_resolution_precision': round(correct_auto / max(1, auto_count), 4),
            'auto_resolution_recall_on_safe_cases': round(correct_auto / max(1, expected_auto), 4),
            'false_auto_resolution_rate': round(false_auto / max(1, total), 4),
            'review_or_abstain_rate': round(review_count / max(1, total), 4),
        },
        'cases': rows,
    }


if __name__ == '__main__':
    result = asyncio.run(evaluate())
    output = ROOT / 'evals' / 'results.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['summary'], indent=2))
    if result['summary']['false_auto_resolution_rate'] > 0:
        raise SystemExit('resolution safety gate failed: false auto-resolution detected')
