"""Tests for the SQLite state manager."""

import asyncio
from pathlib import Path

import pytest
import pytest_asyncio

from src.core.state_manager import StateManager
from src.models.result import ConfidenceLevel, ResultStatus, ScanResult, ScanState


@pytest_asyncio.fixture
async def sm(tmp_path: Path):
    """Create a StateManager backed by a temp database."""
    manager = StateManager(db_path=tmp_path / "test.db")
    await manager.connect()
    yield manager
    await manager.close()


@pytest.mark.asyncio
async def test_create_and_get_session(sm: StateManager):
    state = ScanState(pending_queries=["q1", "q2"])
    await sm.create_session(state)

    loaded = await sm.get_session(state.scan_id)
    assert loaded is not None
    assert loaded.scan_id == state.scan_id
    assert loaded.pending_queries == ["q1", "q2"]
    assert loaded.is_complete is False


@pytest.mark.asyncio
async def test_update_session(sm: StateManager):
    state = ScanState()
    await sm.create_session(state)

    state.completed_queries = ["done1"]
    state.is_complete = True
    state.total_results = 5
    await sm.update_session(state)

    loaded = await sm.get_session(state.scan_id)
    assert loaded.completed_queries == ["done1"]
    assert loaded.is_complete is True
    assert loaded.total_results == 5


@pytest.mark.asyncio
async def test_save_and_get_results(sm: StateManager):
    state = ScanState()
    await sm.create_session(state)

    result = ScanResult(
        module="test_mod",
        query="john doe",
        platform="GitHub",
        url="https://github.com/johndoe",
        status=ResultStatus.FOUND,
        confidence=ConfidenceLevel.HIGH,
    )
    await sm.save_result(state.scan_id, result)

    results = await sm.get_results(state.scan_id)
    assert len(results) == 1
    assert results[0].module == "test_mod"
    assert results[0].status == ResultStatus.FOUND


@pytest.mark.asyncio
async def test_get_latest_incomplete(sm: StateManager):
    s1 = ScanState()
    s1.is_complete = True
    await sm.create_session(s1)

    s2 = ScanState()
    await sm.create_session(s2)

    latest = await sm.get_latest_incomplete_session()
    assert latest is not None
    assert latest.scan_id == s2.scan_id


@pytest.mark.asyncio
async def test_count_results(sm: StateManager):
    state = ScanState()
    await sm.create_session(state)

    for i in range(3):
        r = ScanResult(module="m", query=f"q{i}")
        await sm.save_result(state.scan_id, r)

    assert await sm.count_results(state.scan_id) == 3
