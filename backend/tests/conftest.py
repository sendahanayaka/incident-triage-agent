"""Pytest fixtures for backend API testing."""

import tempfile
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.api.dependencies import get_settings
from backend.app.main import app


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test isolation."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        yield Path(d)


@pytest.fixture
def test_settings(temp_dir: Path) -> Settings:
    """Provide a test Settings instance pointing to temporary stores."""
    db_path = temp_dir / "test_incidents.db"
    trace_path = temp_dir / "test_traces.jsonl"
    return Settings(
        app_name="IncidentTriageAgentTest",
        app_env="test",
        database_path=str(db_path),
        trace_file_path=str(trace_path),
        llm_api_key="",  # Ensure tests don't make real external calls
        llm_model="",
    )


@pytest.fixture
def client(test_settings: Settings) -> Generator[TestClient, None, None]:
    """Provide a TestClient with overridden dependencies."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
