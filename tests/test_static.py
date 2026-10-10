def test_root_serves_login_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="login-form"' in response.text


def test_map_serves_map_page(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert 'id="map"' in response.text


def test_favicon_serves_image(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_register_serves_register_page(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert 'id="register-form"' in response.text


def test_login_page_links_to_register(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'href="/register"' in response.text


# --- login-map-ui (T1): new behavior ---

def test_login_page_wires_real_auth_flow(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "/auth/login" in response.text
    assert "itertrack_token" in response.text
    assert "application/x-www-form-urlencoded" in response.text


def test_login_page_uses_v8_poppins_design(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Poppins" in response.text


def test_map_page_guards_with_auth_me(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "/auth/me" in response.text
    assert "Bearer" in response.text


def test_map_page_has_theme_toggle_hook(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "itertrack_theme" in response.text
    assert 'id="themeBtn"' in response.text


def test_map_page_has_dark_theme_palette(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert ":root.dark" in response.text


def test_map_page_has_logout_button(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert 'id="btn-logout"' in response.text


def test_map_page_uses_example_cdn_leaflet(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4" in response.text


# --- login-map-ui (C1): whole UI scaled by 15% (px literals x1.15) ---

def test_pages_use_scaled_ui_scale(client):
    login = client.get("/")
    page = client.get("/map")
    assert login.status_code == 200
    assert page.status_code == 200
    # Base font sizes: login 14px -> 16px, map 13px -> 15px (with body padding 24px -> 28px)
    assert "font-size:16px" in login.text
    assert "font-size:15px;padding:28px" in page.text
    # Media-query breakpoints: login 860 -> 989, map 820 -> 943
    assert "max-width:989px" in login.text
    assert "max-width:943px" in page.text
