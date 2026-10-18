import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_liveness():
    assert TestClient(app).get("/healthz").json() == {"status": "ok"}


def test_board_requires_login():
    r = TestClient(app).get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
