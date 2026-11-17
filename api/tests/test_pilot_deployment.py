import pytest
from fastapi.testclient import TestClient

from test_pilot import client
from wallnut.database import connect
from wallnut.main import create_app
from wallnut.pilot import PilotError, validate_settings


def web_dist(tmp_path):
    (tmp_path / "index.html").write_text("<title>Wallnut</title>", encoding="utf-8")
    (tmp_path / "manifest.webmanifest").write_text('{"name":"Wallnut"}', encoding="utf-8")
    (tmp_path / "sw.js").write_text("", encoding="utf-8")
    return str(tmp_path)


def test_readiness_reports_pending_migrations_without_exposing_database_details(client):
    ready = client.get("/v1/ready")
    assert ready.status_code == 200 and ready.json() == {"status": "ready"}
    assert ready.headers["cache-control"] == "no-store"

    with connect() as db:
        db.execute("DELETE FROM migrations WHERE name = '013_tournament_pairs.sql'")
    pending = client.get("/v1/ready")
    assert pending.status_code == 503 and pending.json() == {"status": "not_ready"}
    assert client.get("/health").json() == {"status": "ok"}


def test_compiled_website_and_api_share_an_origin(client, monkeypatch, tmp_path):
    monkeypatch.setenv("WEB_DIST_DIR", web_dist(tmp_path))
    hosted = TestClient(create_app())
    assert hosted.get("/").text == "<title>Wallnut</title>"
    assert hosted.get("/manifest.webmanifest").json() == {"name": "Wallnut"}
    assert hosted.get("/v1/ready").json() == {"status": "ready"}
    assert hosted.get("/v1/campus-events").status_code == 401


def test_pilot_settings_require_https_and_a_dedicated_database(monkeypatch, tmp_path):
    monkeypatch.setenv("WEB_DIST_DIR", web_dist(tmp_path))
    monkeypatch.setenv("WALLNUT_PUBLIC_ORIGIN", "https://wallnut.example.edu")
    monkeypatch.setenv("GOOGLE_CLIENT_IDS", "prueba.apps.googleusercontent.com")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PGDATABASE", "wallnut_pilot")
    validate_settings()

    with monkeypatch.context() as configured:
        configured.setenv("WALLNUT_PUBLIC_ORIGIN", "http://wallnut.example.edu")
        with pytest.raises(PilotError, match="HTTPS"):
            validate_settings()
    with monkeypatch.context() as configured:
        configured.setenv("GOOGLE_CLIENT_IDS", "")
        with pytest.raises(PilotError, match="GOOGLE_CLIENT_IDS"):
            validate_settings()
    with monkeypatch.context() as configured:
        configured.setenv("DATABASE_URL", "postgresql://localhost/wallnut_demo")
        with pytest.raises(PilotError, match="distinta de wallnut_demo"):
            validate_settings()
