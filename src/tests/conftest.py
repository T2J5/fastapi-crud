from src.db.main import get_session
from unittest.mock import AsyncMock, patch, Mock
from src import app
import pytest
from fastapi.testclient import TestClient

mock_session = Mock()
mock_user_service = Mock()


def get_mock_session():
    yield mock_session


app.dependency_overrides[get_session] = get_mock_session


@pytest.fixture(autouse=True)
def fake_session():
    return mock_session


@pytest.fixture
def fake_user_service():
    return mock_user_service


@pytest.fixture
def test_client():
    return TestClient(app)
