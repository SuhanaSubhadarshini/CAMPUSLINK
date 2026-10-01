import os
import tempfile
from pathlib import Path

import pytest

# Configure before importing app modules; tests never touch the demo database.
_temp = tempfile.TemporaryDirectory(prefix="campuslink-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(_temp.name) / "test.db").as_posix()
os.environ["UPLOAD_DIR"] = str(Path(_temp.name) / "uploads")
os.environ["SEED_DEMO"] = "true"
os.environ["ADZUNA_APP_ID"] = ""
os.environ["ADZUNA_APP_KEY"] = ""

from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    _temp.cleanup()


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as test_client:
        yield test_client
