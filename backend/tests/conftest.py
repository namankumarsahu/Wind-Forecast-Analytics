import pytest
from fastapi.testclient import TestClient

from app.deps import get_service
from app.main import create_app
from app.services.analysis import AnalysisService
from app.services.policy import DecisionPolicy
from datetime import date

from .factories import FakeProvider


@pytest.fixture
def make_client():
    """Build a TestClient whose service reads deterministic synthetic data (or a custom provider)."""
    clients = []

    def _make(provider=None) -> TestClient:
        app = create_app()
        service = AnalysisService(provider or FakeProvider(), DecisionPolicy(), date(2026, 1, 1), date(2026, 1, 31))
        app.dependency_overrides[get_service] = lambda: service
        client = TestClient(app)
        clients.append(client)
        return client

    yield _make
