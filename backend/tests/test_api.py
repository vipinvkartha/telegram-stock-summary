from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import create_app


def test_health_endpoint(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHANNELS", "")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_backfill_requires_configured_admin_token(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHANNELS", "")
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.post("/telegram/backfill", json={"limit_per_channel": 10})

    assert response.status_code == 503


def test_backfill_requires_matching_admin_token(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHANNELS", "")
    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.post(
            "/telegram/backfill",
            headers={"X-Admin-Token": "wrong"},
            json={"limit_per_channel": 10},
        )

    assert response.status_code == 401


def test_backfill_returns_result_with_valid_admin_token(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHANNELS", "")
    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.post(
            "/telegram/backfill",
            headers={"X-Admin-Token": "secret"},
            json={"limit_per_channel": 10},
        )

    assert response.status_code == 200
    assert response.json()["total_seen"] == 0
