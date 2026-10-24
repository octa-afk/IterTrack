"""SPA serving: the built React app replaces the retired vanilla pages."""

import re
from pathlib import Path

import pytest

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
requires_build = pytest.mark.skipif(
    not (DIST / "index.html").is_file(),
    reason="frontend build missing; run: npm --prefix frontend run build",
)


@requires_build
@pytest.mark.parametrize("route", ["/", "/register", "/map", "/fleet", "/viajes"])
def test_routes_serve_the_spa_shell(client, route):
    response = client.get(route)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="root"' in response.text
    assert re.search(r'src="/assets/index-[^"]+\.js"', response.text)
    assert re.search(r'href="/assets/index-[^"]+\.css"', response.text)


def test_favicon_serves_image(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


@pytest.mark.parametrize(
    "path",
    ["/static/js/map.js", "/static/css/map.css", "/static/login.html"],
)
def test_vanilla_frontend_is_retired(client, path):
    assert client.get(path).status_code == 404


@requires_build
def test_built_js_asset_is_served(client):
    html = client.get("/").text
    match = re.search(r'/assets/(index-[^"]+\.js)', html)
    assert match is not None, f"no hashed JS asset referenced in {html[:200]}"
    asset = match.group(1)
    response = client.get(f"/assets/{asset}")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_missing_build_returns_503(client, monkeypatch, tmp_path):
    monkeypatch.setattr("source.main.FRONTEND_DIST", tmp_path)
    response = client.get("/")
    assert response.status_code == 503
    assert "npm --prefix frontend run build" in response.json()["detail"]
