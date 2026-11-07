from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def contention_dump() -> Path:
    return EXAMPLES / "sample_thread_dump.txt"


@pytest.fixture
def deadlock_dump() -> Path:
    return EXAMPLES / "sample_deadlock_thread_dump.txt"


@pytest.fixture
def mat_histogram() -> Path:
    return EXAMPLES / "sample_heap_summary.txt"
