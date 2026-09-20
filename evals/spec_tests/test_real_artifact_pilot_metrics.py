import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_real_artifact_pilot import evaluate_case, summarize_rows


def _payload(*, hint_name, candidate_names):
    return {
        'memory': {
            'id': 1,
            'resolution_status': 'needs_review',
            'resolution_method': None,
            'hint': {'name': hint_name},
            'candidates': [
                {'name': name}
                for name in candidate_names
            ],
            'place': None,
            'pre_resolution_confidence': 0.7,
            'pre_resolution_gap': 0.05,
        }
    }


def test_ground_truth_is_separate_from_supported_extraction():
    case = {
        'case': 'insufficient-artifact',
        'scenario': 'known ground truth but insufficient evidence',
        'ground_truth_name': 'Actual Place',
        'ground_truth_city': 'New York',
        'ground_truth_source': 'verified external source',
        'ground_truth_notes': 'Artifact came from this place.',
        'expected_extraction_name': None,
        'expected_mode': 'review',
    }

    row = evaluate_case(
        case,
        _payload(
            hint_name=None,
            candidate_names=[],
        ),
    )

    assert row['ground_truth_name'] == 'Actual Place'
    assert row['extracted_name'] is None
    assert row['extraction_correct'] is True


def test_top1_is_conditional_on_successful_retrieval():
    retrieved = {
        'mode_correct': True,
        'extraction_correct': True,
        'correct_candidate_seen': True,
        'top1_given_retrieval': True,
        'false_auto': False,
    }
    missed = {
        'mode_correct': True,
        'extraction_correct': True,
        'correct_candidate_seen': False,
        'top1_given_retrieval': None,
        'false_auto': False,
    }

    summary = summarize_rows([retrieved, missed])

    assert summary['candidate_recall_at_k_on_labeled_cases'] == 0.5
    assert summary['top1_accuracy_given_successful_retrieval'] == 1.0
    assert summary['candidate_labeled_cases'] == 2
    assert summary['successful_retrieval_cases'] == 1
