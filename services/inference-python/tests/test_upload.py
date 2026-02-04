from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
import app.main as main
from app.main import app


def test_upload_files(tmp_path: Path, monkeypatch):
    get_settings.cache_clear()
    (tmp_path / "uploads").mkdir(parents=True, exist_ok=True)

    # override upload dir
    import os

    os.environ["UPLOAD_DIR"] = str(tmp_path / "uploads")
    get_settings.cache_clear()

    monkeypatch.setattr(main, "embed_text", lambda *_args, **_kwargs: [0.1, 0.2, 0.3])
    monkeypatch.setattr(main, "ensure_collection", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main, "upsert_chunks", lambda *_args, **_kwargs: 1)

    client = TestClient(app)
    files = [("files", ("notes/hello.txt", b"hello world", "text/plain"))]
    response = client.post("/v1/files/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["total_bytes"] == len(b"hello world")
    assert "notes/hello.txt" in data["files"]
    assert "indexed_chunks" in data
    assert (tmp_path / "uploads" / "notes" / "hello.txt").exists()


def test_upload_missing_files():
    client = TestClient(app)
    response = client.post("/v1/files/upload")
    assert response.status_code == 422
