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


# --- register-ui (T1): v10 register page wiring (create/join + auto-login) ---

def test_register_page_wires_real_auth_flow(client):
    response = client.get("/register")
    assert response.status_code == 200
    # Test hook + real API contract
    assert 'id="register-form"' in response.text
    assert 'action="/auth/register"' in response.text
    assert "/auth/login" in response.text
    assert "application/x-www-form-urlencoded" in response.text
    assert "itertrack_token" in response.text
    assert "REDIRECT = '/map'" in response.text  # redirect target, same style as login.html
    # Create-organization vs join-with-code mode survives the redesign
    assert 'id="mode-create"' in response.text
    assert 'id="mode-join"' in response.text
    # New v10 form hooks (submit button now carries an id)
    assert 'id="submit"' in response.text


# --- register-ui (T2): v10 reference design markers (same family as login.html) ---

def test_register_page_uses_v10_poppins_design(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert "Poppins" in response.text
    assert 'class="shell"' in response.text   # two-panel glass shell
    assert 'class="brand"' in response.text   # brand panel with live fleet card
    assert 'class="meter"' in response.text   # password strength meter
    # 15%-scaled tokens: 1020px shell -> 1173px, 860px breakpoint -> 989px
    assert "max-width:1173px" in response.text
    assert "max-width:989px" in response.text


def test_register_page_links_to_login_route(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert 'href="/"' in response.text
    assert 'href="login.html"' not in response.text


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


def test_map_page_uses_light_cartography_only(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "maplibre-gl@5.24.0/dist/maplibre-gl.css" in response.text
    assert "maplibre-gl@5.24.0/dist/maplibre-gl.js" in response.text
    assert "@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js" in response.text
    assert "tiles.openfreemap.org/styles/bright" in response.text
    assert "tiles.openfreemap.org/styles/dark" not in response.text
    assert "function neutralizeBuildings" in response.text
    assert "sourceLayer === 'building'" in response.text
    assert "fill-extrusion-opacity', 0" in response.text
    assert "mapLibreMap.on('style.load', neutralizeBuildings)" in response.text
    assert "themeBtn" not in response.text
    assert ":root.dark" not in response.text
    assert "L.maplibreGL" in response.text


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


# --- login-map-ui (C2): truck marker redesign (SVG truck, status halo, plate label) ---

def test_map_page_renders_truck_marker_design(client):
    response = client.get("/map")
    assert response.status_code == 200
    # The arrow pointer is replaced by the supplied vertical truck SVG.
    assert 'viewBox="-36 -76 72 152"' in response.text
    assert 'fill="#F26B1D"' in response.text
    assert ".pin svg{width:18px;height:38px}" in response.text
    assert "const arrow" not in response.text
    assert "${truckSvg(t.color)}" in response.text
    # divIcon box matches .pin and the anchor stays exactly half of iconSize
    assert "iconSize:[40,40]" in response.text
    assert "iconAnchor:[20,20]" in response.text
    # The supplied truck is rendered directly, without a circular badge or halo.
    assert "const truckSvg" in response.text
    assert 'replaceAll(\'#F26B1D\', color)' in response.text
    assert "replaceAll('#F9955A', '#FFFFFF')" in response.text
    assert 'class="truck-svg"' in response.text
    assert 'class="halo"' not in response.text
    assert 'class="badge"' not in response.text
    assert ".pin .lbl" in response.text
    assert ".pin.sel .truck-svg" in response.text


# --- login-map-ui (C2c): truck moves between samples instead of teleporting ---

def test_map_page_animates_truck_movement(client):
    response = client.get("/map")
    assert response.status_code == 200
    # Two received samples are tweened on a rAF loop, clamped to a sane duration
    assert "requestAnimationFrame" in response.text
    assert "function programarMovimiento" in response.text
    assert "function tickMovimiento" in response.text
    assert "MOVE_MAX_MS" in response.text
    # render() must not jump the pin straight to the newest sample anymore
    assert "mk.setLatLng([t.lat,t.lng]).setIcon(" not in response.text
    # Longitude deltas must be converted to radians before bearing math;
    # the truck SVG points north at zero degrees and rotates clockwise.
    assert "Math.sin(toRad(bLng - aLng))" in response.text
    assert "Math.cos(toRad(bLng - aLng))" in response.text


# --- login-map-ui (C2d): one stable identity color per truck + map opens on a truck ---

def test_map_page_gives_truck_a_stable_color(client):
    response = client.get("/map")
    assert response.status_code == 200
    # The pin keeps a per-truck identity color instead of recoloring with status
    assert "TRUCK_COLORS" in response.text
    assert "function colorDeCamion" in response.text
    assert "truckSvg(t.color)" in response.text
    assert 'badge" style="background:${STATUS[t.status].color}' not in response.text


def test_map_page_opens_centered_on_first_truck(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "function centrarEnPrimerCamion" in response.text
    # Boot must center after the first real location poll, not on the default view
    assert "centrarEnPrimerCamion();" in response.text


def test_map_page_discovers_trucks_during_polling(client):
    response = client.get("/map")
    assert response.status_code == 200
    # Each live poll must reconcile the org-scoped list without resetting
    # telemetry state for trucks that are still present.
    assert "function crearEstadoCamion" in response.text
    assert "await cargarCamiones();" in response.text
    assert "const existentes = new Map(trucks.map" in response.text
    assert "markers.delete(id)" in response.text
    assert "moves.delete(id)" in response.text


# --- login-map-ui (C2e): v10 chrome — collapsible sidebar + solid top bar ---

def test_map_page_has_collapsible_sidebar_and_solid_topbar(client):
    response = client.get("/map")
    assert response.status_code == 200
    # Sidebar wrapper, toggle button and the mini brand shown when it is hidden
    assert 'id="sidebar"' in response.text
    assert 'class="side-in"' in response.text
    assert 'id="navToggle"' in response.text
    assert 'class="tl"' in response.text
    assert ".minibrand" in response.text
    assert ".app.nav-off" in response.text
    # The toggle state is persisted per browser, like the theme
    assert "itertrack-nav" in response.text
    # The project's own hooks survive the port (the v10 example has neither)
    assert 'id="btn-logout"' in response.text


# --- login-map-ui (C3): v10 glass dashboard layer ---

def test_map_page_has_v10_glass_fullscreen_layer(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "--g-bg:rgba(255,255,255,.64)" in response.text
    assert ".content,.grid,.grid>.col:first-child,.mapcard{display:contents}" in response.text
    assert ".mapbox{position:absolute;inset:0;z-index:0" in response.text
    assert ".side,.top,.card,.mapcard .card-h,.leaflet-bar,.leaflet-control-attribution" in response.text
    assert ".leaflet-top.leaflet-left{left:var(--lx);top:147px}" in response.text
    assert "@media (max-width:1265px)" in response.text


def test_map_page_preserves_real_hooks_with_glass_layer(client):
    response = client.get("/map")
    assert response.status_code == 200
    for hook in ('id="map"', 'id="liveTag"', 'id="bars"', 'id="donuts"',
                 'id="detail"', 'id="list"', 'id="q"', 'id="sort"',
                 'id="dir"', 'id="chips"', 'id="seg"', 'id="alertBtn"',
                 'id="btn-logout"', 'id="navToggle"'):
        assert hook in response.text
    assert "fetch('/auth/me'" in response.text
    assert "fetch('/trucks'" in response.text
    assert "function actualizarUbicaciones" in response.text
