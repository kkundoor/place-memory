import argparse
import json
import mimetypes
from pathlib import Path

import httpx


def observed_mode(memory):
    status = memory.get('resolution_status')
    if status == 'resolved':
        return 'auto' if memory.get('resolution_method') == 'auto' else 'manual'
    if status == 'needs_review':
        return 'review'
    return 'abstain'


def evaluate_case(case, payload):
    memory = payload['memory']
    candidates = memory.get('candidates') or payload.get('candidates') or []
    expected_names = {x.casefold() for x in case.get('expected_candidate_names') or []}

    rank = None
    for i, candidate in enumerate(candidates, start=1):
        if (candidate.get('name') or '').casefold() in expected_names:
            rank = i
            break

    expected_mode = case.get('expected_mode')
    mode = observed_mode(memory)
    extraction_labeled = 'expected_extraction_name' in case
    expected_extract = case.get('expected_extraction_name')
    extracted = (memory.get('hint') or {}).get('name')

    if not extraction_labeled:
        extraction_correct = None
    elif expected_extract is None:
        extraction_correct = extracted is None
    else:
        extraction_correct = (
            (extracted or '').casefold()
            == expected_extract.casefold()
        )

    return {
        'case': case['case'],
        'scenario': case.get('scenario'),
        'expected_mode': expected_mode,
        'observed_mode': mode,
        'mode_correct': None if expected_mode is None else mode == expected_mode,
        'expected_extraction_name': expected_extract,
        'extracted_name': extracted,
        'extraction_correct': extraction_correct,
        'correct_candidate_seen': None if not expected_names else rank is not None,
        'correct_candidate_rank': rank,
        'false_auto': mode == 'auto' and expected_mode not in (None, 'auto'),
        'selected_name': (memory.get('place') or {}).get('name'),
        'top_confidence': memory.get('pre_resolution_confidence'),
        'top_gap': memory.get('pre_resolution_gap'),
        'memory_id': memory.get('id'),
        'hint': memory.get('hint'),
        'candidates': candidates,
    }


def ratio(values):
    values = [x for x in values if x is not None]
    return None if not values else round(sum(bool(x) for x in values) / len(values), 4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', default='artifacts/real-pilot/manifest.json')
    parser.add_argument('--api', default='http://localhost:8000')
    parser.add_argument(
        '--case',
        action='append',
        dest='case_names',
        help='run only the named case; may be supplied more than once',
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    base_dir = manifest_path.parent

    rows = []
    with httpx.Client(timeout=60) as client:
        for case in manifest['cases']:
            if case.get('skip'):
                continue
            if args.case_names and case['case'] not in args.case_names:
                continue

            artifact = case.get('artifact_path')
            context = (case.get('context') or '').strip()
            source_url = (case.get('source_url') or '').strip()

            if artifact:
                path = (base_dir / artifact).resolve()
                if not path.exists():
                    raise FileNotFoundError(f"{case['case']}: missing {path}")
                mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
                with path.open('rb') as handle:
                    response = client.post(
                        f'{args.api}/api/memories/ingest-image',
                        files={'image': (path.name, handle, mime)},
                        data={k: v for k, v in {'note': context, 'source_url': source_url}.items() if v},
                    )
            elif context:
                response = client.post(
                    f'{args.api}/api/memories/ingest',
                    json={
                        'source_type': 'link' if source_url else 'note',
                        'source_text': context,
                        'source_url': source_url or None,
                    },
                )
            else:
                raise ValueError(f"{case['case']}: provide artifact_path or context")

            if response.status_code != 200:
                raise RuntimeError(f"{case['case']}: HTTP {response.status_code}: {response.text}")

            row = evaluate_case(case, response.json())
            rows.append(row)
            print(
                f"{row['case']}: extract={row['extracted_name']!r} "
                f"rank={row['correct_candidate_rank']} "
                f"decision={row['observed_mode']} "
                f"selected={row['selected_name']!r}"
            )

    labeled_modes = [r['mode_correct'] for r in rows if r['mode_correct'] is not None]
    labeled_extract = [r['extraction_correct'] for r in rows if r['extraction_correct'] is not None]
    labeled_recall = [r['correct_candidate_seen'] for r in rows if r['correct_candidate_seen'] is not None]
    labeled_top1 = [r['correct_candidate_rank'] == 1 for r in rows if r['correct_candidate_seen'] is not None]

    summary = {
        'cases_run': len(rows),
        'extraction_accuracy_on_labeled_cases': ratio(labeled_extract),
        'candidate_recall_at_k_on_labeled_cases': ratio(labeled_recall),
        'top1_accuracy_on_labeled_cases': ratio(labeled_top1),
        'decision_mode_accuracy_on_labeled_cases': ratio(labeled_modes),
        'false_auto_count': sum(1 for r in rows if r['false_auto']),
        'false_auto_resolution_rate': None if not labeled_modes else round(sum(1 for r in rows if r['false_auto']) / len(labeled_modes), 4),
    }

    result = {'corpus': 'real-artifact-pilot', 'summary': summary, 'cases': rows}
    output = base_dir / 'results.json'
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print()
    print(json.dumps(summary, indent=2))
    print(f'results written to {output}')


if __name__ == '__main__':
    main()
