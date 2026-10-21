def test_root_serves_react_entrypoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text
    assert "/src/main.tsx" not in response.text


def test_map_serves_react_entrypoint(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text


def test_register_serves_react_entrypoint(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text


def test_react_entrypoint_preserves_auth_and_dashboard_bundle(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "/assets/" in response.text


def test_react_bundle_asset_is_served(client):
    entrypoint = client.get("/")
    asset_path = next(
        part.split('"', 1)[0]
        for part in entrypoint.text.split('src="')
        if part.startswith("/assets/")
    )
    asset = client.get(asset_path)
    assert asset.status_code == 200
    assert "javascript" in asset.headers["content-type"]


def test_favicon_serves_image(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
