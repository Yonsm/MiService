import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import json


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_config():
    """Provide a mock configuration dictionary."""
    return {
        "user": "test_user@example.com",
        "password": "test_password",
        "device_id": "test_device_123",
        "server": "https://api.test.xiaomi.com",
    }


@pytest.fixture
def mock_token_store(temp_dir):
    """Create a mock token store file."""
    token_file = temp_dir / ".mi.token"
    token_data = {
        "userId": "12345",
        "serviceToken": "test_service_token",
        "ssecurity": "test_ssecurity",
    }
    token_file.write_text(json.dumps(token_data))
    return token_file


@pytest.fixture
def mock_session():
    """Create a mock aiohttp ClientSession."""
    session = AsyncMock()
    session.get = AsyncMock()
    session.post = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"code": 0, "data": {}})
    response.text = AsyncMock(return_value='{"code": 0, "data": {}}')
    response.headers = {"Content-Type": "application/json"}
    return response


@pytest.fixture
def mock_device_list():
    """Provide a mock device list response."""
    return {
        "code": 0,
        "data": {
            "list": [
                {
                    "did": "test_device_123",
                    "name": "Test Device",
                    "model": "test.model.v1",
                    "isOnline": True,
                },
                {
                    "did": "test_device_456",
                    "name": "Another Device",
                    "model": "test.model.v2",
                    "isOnline": False,
                },
            ]
        }
    }


@pytest.fixture
def mock_mi_account(mock_session):
    """Create a mock MiAccount instance."""
    account = MagicMock()
    account.session = mock_session
    account.user = "test_user@example.com"
    account.password = "test_password"
    account.token_store = ".mi.token"
    account.service_token = "test_service_token"
    account.ssecurity = "test_ssecurity"
    account.user_id = "12345"
    return account


@pytest.fixture
def capture_logs():
    """Capture log output for testing."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    logger = logging.getLogger()
    original_handlers = logger.handlers[:]
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    logger.handlers = original_handlers


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    """Reset environment variables for each test."""
    monkeypatch.delenv("MI_USER", raising=False)
    monkeypatch.delenv("MI_PASS", raising=False)
    monkeypatch.delenv("MI_DID", raising=False)


@pytest.fixture
def set_test_environment(monkeypatch):
    """Set test environment variables."""
    monkeypatch.setenv("MI_USER", "test_user@example.com")
    monkeypatch.setenv("MI_PASS", "test_password")
    monkeypatch.setenv("MI_DID", "test_device_123")