import os
import pytest
from fastapi.testclient import TestClient
from main import app
from config.config import Settings, get_settings


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def test_settings():
    return Settings(
        model_path="test_model.pkl",
        log_level="DEBUG",
        redis_predict_ttl_sec=600,
        redis_task_pending_ttl_sec=3,
        redis_task_completed_ttl_sec=3600,
        redis_active_task_ttl_sec=60,
    )


@pytest.fixture(autouse=True)
def override_settings(test_settings):
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides = {}

    if os.path.exists(test_settings.model_path):
        os.remove(test_settings.model_path)
