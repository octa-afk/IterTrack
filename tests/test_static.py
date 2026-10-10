def test_root_serves_login_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="login-form"' in response.text


def test_map_serves_map_page(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert 'id="map"' in response.text


def test_logo_serves_image(client):
    response = client.get("/logo")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_favicon_serves_image(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_login_page_references_logo(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'src="/logo"' in response.text


def test_register_serves_register_page(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert 'id="register-form"' in response.text


def test_login_page_links_to_register(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'href="/register"' in response.text
