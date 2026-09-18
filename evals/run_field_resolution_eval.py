import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'api'))
sys.path.insert(0, str(ROOT / 'evals'))

from app.models import ResolutionStatus  # noqa: E402
from app.services.resolver import resolve_hint  # noqa: E402
from field_cases import CASES  # noqa: E402


class Search:
    def __init__(self, places):
        self.places = places

    async def search_places(self, hint):
        return self.places


async def evaluate() -> dict:
    rows = []
    mode_correct = labeled_top1 = labeled_cases = false_auto = 0
    for case in CASES:
        status, selected, ranked = await resolve_hint(case.hint, Search(case.candidates))
        top_id = ranked[0].place_id if ranked else None
        if case.expected_top_ids:
            labeled_cases += 1
            labeled_top1 += int(top_id in case.expected_top_ids)
        observed_mode = (
            'auto' if status == ResolutionStatus.resolved
            else 'review' if status == ResolutionStatus.needs_review
            else 'abstain'
        )
        correct_mode = observed_mode == case.expected_mode
        mode_correct += int(correct_mode)
        if observed_mode == 'auto' and case.expected_mode != 'auto':
            false_auto += 1
        rows.append({
            'case': case.name,
            'expected_mode': case.expected_mode,
            'observed_mode': observed_mode,
            'mode_correct': correct_mode,
            'top_id': top_id,
            'top_confidence': ranked[0].confidence if ranked else None,
            'expected_top_ids': sorted(case.expected_top_ids),
            'top1_correct': top_id in case.expected_top_ids if case.expected_top_ids else None,
            'candidate_count': len(ranked),
            'selected_id': selected.place_id if selected else None,
        })
    total = len(CASES)
    return {
        'corpus': 'field',
        'summary': {
            'cases': total,
            'decision_mode_accuracy': round(mode_correct / max(1, total), 4),
            'top1_accuracy_on_labeled_cases': round(labeled_top1 / max(1, labeled_cases), 4),
            'false_auto_resolution_rate': round(false_auto / max(1, total), 4),
        },
        'cases': rows,
    }


if __name__ == '__main__':
    result = asyncio.run(evaluate())
    output = ROOT / 'evals' / 'field_results.json'
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(result['summary'], indent=2))
    if result['summary']['false_auto_resolution_rate'] > 0:
        raise SystemExit('field safety gate failed: false auto-resolution detected')
    print('field results written to evals/field_results.json')
