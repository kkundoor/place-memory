import pytest
from fastapi import HTTPException

from app import main


def test_demo_budget_has_a_hard_rolling_limit(monkeypatch):
    main._demo_call_times.clear()

    monkeypatch.setattr(main, 'DEMO_MAX_CALLS_PER_WINDOW', 2)
    monkeypatch.setattr(main, 'DEMO_WINDOW_SECONDS', 3600)

    main._consume_demo_budget()
    main._consume_demo_budget()

    with pytest.raises(HTTPException) as exc_info:
        main._consume_demo_budget()

    assert exc_info.value.status_code == 429
    assert 'temporarily at capacity' in exc_info.value.detail

    main._demo_call_times.clear()
