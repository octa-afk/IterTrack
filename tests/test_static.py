"""Pages, markup, and extracted asset assertions.

Stylesheet contents live in ``tests/test_static_css.py`` now that CSS is served
from ``source/static/css/`` instead of being inlined in each page.
"""

from pathlib import Path
import re


def page_source(response):
    """Return page markup plus local JavaScript assets declared by the page."""
    page = response.text
    pending = [asset.split('"', 1)[0] for asset in page.split('src="/static/js/')[1:]]
    loaded = set()
    while pending:
        name = pending.pop(0)
        if name in loaded:
            continue
        loaded.add(name)
        script = Path("source/static/js", name).read_text()
        page += script
        pending.extend(re.findall(r"from ['\"]\.\/([^'\"]+)", script))
    return page


def test_root_serves_login_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="login-form"' in page_source(response)


def test_map_serves_map_page(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert 'id="map"' in page_source(response)


def test_favicon_serves_image(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_register_serves_register_page(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert 'id="register-form"' in page_source(response)


# --- modularization (T4): pages load their extracted stylesheets ---

def test_pages_link_extracted_stylesheets(client):
    expected = {
        "/": ("auth-tokens.css", "auth.css", "login.css"),
        "/register": ("auth-tokens.css", "auth.css", "register.css"),
        "/map": ("map.css",),
    }
    for route, sheets in expected.items():
        page = client.get(route)
        assert page.status_code == 200
        # The inline block is gone; every page declares its own stylesheets.
        assert "<style>" not in page.text
        for sheet in sheets:
            assert f'href="/static/css/{sheet}"' in page.text


# --- register-ui (T1): v10 register page wiring (create/join + auto-login) ---

def test_register_page_wires_real_auth_flow(client):
    response = client.get("/register")
    assert response.status_code == 200
    # Test hook + real API contract
    assert 'id="register-form"' in page_source(response)
    assert 'action="/auth/register"' in page_source(response)
    assert "/auth/login" in page_source(response)
    assert "application/x-www-form-urlencoded" in page_source(response)
    assert "itertrack_token" in page_source(response)
    assert "REDIRECT = '/map'" in page_source(response)  # redirect target, same style as login.html
    # Create-organization vs join-with-code mode survives the redesign
    assert 'id="mode-create"' in page_source(response)
    assert 'id="mode-join"' in page_source(response)
    # New v10 form hooks (submit button now carries an id)
    assert 'id="submit"' in page_source(response)


# --- register-ui (T2): v10 reference design markers (same family as login.html) ---

def test_register_page_uses_v10_poppins_design(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert "Poppins" in page_source(response)
    assert 'class="shell"' in page_source(response)   # two-panel glass shell
    assert 'class="brand"' in page_source(response)   # brand panel with live fleet card
    assert 'class="meter"' in page_source(response)   # password strength meter


def test_register_page_links_to_login_route(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert 'href="/"' in page_source(response)
    assert 'href="login.html"' not in page_source(response)


def test_login_page_links_to_register(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'href="/register"' in page_source(response)


# --- login-map-ui (T1): new behavior ---

def test_login_page_wires_real_auth_flow(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "/auth/login" in page_source(response)
    assert "itertrack_token" in page_source(response)
    assert "application/x-www-form-urlencoded" in page_source(response)


def test_login_page_uses_v8_poppins_design(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Poppins" in page_source(response)


def test_map_page_guards_with_auth_me(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "/auth/me" in page_source(response)
    assert "Bearer" in page_source(response)


def test_map_page_uses_light_cartography_only(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "maplibre-gl@5.24.0/dist/maplibre-gl.css" in page_source(response)
    assert "maplibre-gl@5.24.0/dist/maplibre-gl.js" in page_source(response)
    assert "@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js" in page_source(response)
    assert "tiles.openfreemap.org/styles/bright" in page_source(response)
    assert "tiles.openfreemap.org/styles/dark" not in page_source(response)
    assert "function neutralizeBuildings" in page_source(response)
    assert "sourceLayer === 'transportation'" in page_source(response)
    assert "setPaintProperty(layer.id, 'line-color'" in page_source(response)
    assert "originalRoadLineColors" in page_source(response)
    assert "event.code !== 'KeyR'" in page_source(response)
    assert "window.matchMedia('(min-width: 944px)').matches" in page_source(response)
    assert "sourceLayer === 'building'" in page_source(response)
    assert "fill-extrusion-opacity', 0" in page_source(response)
    assert "mapLibreMap.on('style.load', neutralizeBuildings)" in page_source(response)
    assert "themeBtn" not in page_source(response)
    assert ":root.dark" not in page_source(response)
    assert "L.maplibreGL" in page_source(response)


def test_map_page_has_logout_button(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert 'id="btn-logout"' in page_source(response)


def test_map_page_uses_example_cdn_leaflet(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4" in page_source(response)


# --- login-map-ui (C2): truck marker redesign (SVG truck, status halo, plate label) ---

def test_map_page_renders_truck_marker_design(client):
    response = client.get("/map")
    assert response.status_code == 200
    # The marker uses the supplied articulated-truck SVG, with the cab pointing up.
    assert 'viewBox="0 0 48 72"' in page_source(response)
    assert 'fill="#2563EB"' in page_source(response)
    assert "const arrow" not in page_source(response)
    # The marker SVG is static; plate text is added separately with textContent.
    assert "vehicle.innerHTML = TRUCK_SVG" in page_source(response)
    # The icon is anchored at its center so the truck sits on its real coordinate.
    assert "iconSize: [48, 48]" in page_source(response)
    assert "iconAnchor: [24, 24]" in page_source(response)
    # The supplied truck is rendered directly, without a separate halo.
    assert "const TRUCK_SVG" in page_source(response)
    assert "vehicle.className = 'truck-svg'" in page_source(response)
    assert 'class="halo"' not in page_source(response)
    assert 'class="badge"' not in page_source(response)
    # Heading travels through a CSS variable; an inline transform would override
    # the selection scale declared in the stylesheet.
    assert "vehicle.style.setProperty('--heading', `${truck.heading}deg`)" in page_source(response)


# --- login-map-ui (C2c): truck moves between samples instead of teleporting ---

def test_map_page_animates_truck_movement(client):
    response = client.get("/map")
    assert response.status_code == 200
    # Two received samples are tweened on a rAF loop, clamped to a sane duration
    assert "requestAnimationFrame" in page_source(response)
    assert "function programarMovimiento" in page_source(response)
    assert "function tick()" in page_source(response)
    assert "MOVE_MAX_MS" in page_source(response)
    # render() must not jump the pin straight to the newest sample anymore
    assert "mk.setLatLng([t.lat,t.lng]).setIcon(" not in page_source(response)
    # Longitude deltas must be converted to radians before bearing math;
    # the truck SVG points north at zero degrees and rotates clockwise.
    assert "Math.sin(toRad(bLng - aLng))" in page_source(response)
    assert "Math.cos(toRad(bLng - aLng))" in page_source(response)


# --- read endpoints order by recorded_at: the speed history uses the same time base ---

def test_map_page_history_delta_uses_recorded_at_field(client):
    response = client.get("/map")
    assert response.status_code == 200
    # /iter pairs come ordered by recorded_at, so their time delta must use recorded_at too
    assert "Date.parse(current.recorded_at) - Date.parse(previous.recorded_at)" in page_source(response)
    assert "Date.parse(current.timestamp)" not in page_source(response)


# --- login-map-ui (C2d): one stable identity color per truck + map opens on a truck ---

def test_map_page_gives_truck_a_stable_color(client):
    response = client.get("/map")
    assert response.status_code == 200
    # The pin keeps a per-truck identity color instead of recoloring with status
    assert "TRUCK_COLORS" in page_source(response)
    assert "function colorDeCamion" in page_source(response)
    assert "createTruckIcon" in page_source(response)
    assert 'badge" style="background:${STATUS[t.status].color}' not in page_source(response)


def test_map_page_opens_centered_on_first_truck(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert "function centrarEnPrimerCamion" in page_source(response)
    # Boot must center after the first real location poll, not on the default view
    assert "centrarEnPrimerCamion();" in page_source(response)


def test_map_page_discovers_trucks_during_polling(client):
    response = client.get("/map")
    assert response.status_code == 200
    # Each live poll must reconcile the org-scoped list without resetting
    # telemetry state for trucks that are still present.
    assert "function crearEstadoCamion" in page_source(response)
    assert "await syncTrucks({ map, createTruckState: crearEstadoCamion });" in page_source(response)
    assert "const existing = new Map(getTruckList().map" in page_source(response)
    assert "getMarkers().delete(id)" in page_source(response)
    assert "getMoves().delete(id)" in page_source(response)


# --- login-map-ui (C2e): v10 chrome — collapsible sidebar + solid top bar ---

def test_map_page_has_collapsible_sidebar_and_solid_topbar(client):
    response = client.get("/map")
    assert response.status_code == 200
    # Sidebar wrapper, toggle button and the mini brand shown when it is hidden
    assert 'id="sidebar"' in page_source(response)
    assert 'class="side-in"' in page_source(response)
    assert 'id="navToggle"' in page_source(response)
    assert 'class="tl"' in page_source(response)
    # The toggle state is persisted per browser, like the theme
    assert "itertrack-nav" in page_source(response)
    # The project's own hooks survive the port (the v10 example has neither)
    assert 'id="btn-logout"' in page_source(response)


# --- login-map-ui (C3): v10 glass dashboard layer ---

def test_map_page_preserves_real_hooks_with_glass_layer(client):
    response = client.get("/map")
    assert response.status_code == 200
    for hook in ('id="map"', 'id="liveTag"', 'id="bars"', 'id="donuts"',
                 'id="detail"', 'id="list"', 'id="q"', 'id="sort"',
                 'id="dir"', 'id="chips"', 'id="seg"', 'id="alertBtn"',
                 'id="btn-logout"', 'id="navToggle"'):
        assert hook in page_source(response)
    assert "fetch('/auth/me'" in page_source(response)
    assert "fetch('/trucks'" in page_source(response)
    assert "function actualizarUbicaciones" in page_source(response)


def test_map_page_integrates_mobile_tabs_with_live_map_only(client):
    response = client.get("/map")
    assert response.status_code == 200
    page = page_source(response)

    assert 'id="mobile-tabs"' in page
    for view in ("panel", "fleet", "map"):
        assert f'data-mobile-view="{view}"' in page
    assert "function setMobileView(view)" in page
    assert "requestAnimationFrame(() => map.invalidateSize())" in page
    assert "L.map('map')" in page
    assert "fetch('/auth/me'" in page
    assert "fetch('/trucks'" in page
    assert "function actualizarUbicaciones" in page
    assert "label.textContent = truck.plate" in page
    assert '<em class="lbl" style="font-style:normal">${t.plate}' not in page

    # The visual prototype's simulated fleet and coordinate-grid map stay out
    # of the authenticated page; its existing requestAnimationFrame movement
    # tween is legitimate because it animates received GPS samples.
    assert "const NAMES" not in page
    assert "Math.random()" not in page
    assert 'id="world"' not in page
    assert "const W = 2400" not in page
    assert "function loop(now)" not in page
