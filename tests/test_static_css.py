"""Assertions for the stylesheets served from ``/static/css/``.

These rules used to be asserted against the page HTML while each page carried an
inline ``<style>`` block. They now read the extracted sheet, so the design intent
stays covered after the modularization.
"""


def sheet(client, name):
    response = client.get(f"/static/css/{name}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    return response.text


# --- login-map-ui (C1): whole UI scaled by 15% (px literals x1.15) ---

def test_auth_shell_keeps_the_scaled_v10_geometry(client):
    text = sheet(client, "auth.css")
    # Base font 14px -> 16px; 1020px shell -> 1173px; 860 -> 989 breakpoint
    assert "font-size:16px" in text
    assert "max-width:1173px" in text
    assert "max-width:989px" in text


def test_map_sheet_keeps_the_scaled_ui_scale(client):
    text = sheet(client, "map.css")
    # Base font 13px -> 15px with body padding 24px -> 28px; 820 -> 943 breakpoint
    assert "font-size:15px;padding:28px" in text
    assert "max-width:943px" in text


# --- login-map-ui (C2): truck marker redesign ---

def test_map_sheet_keeps_the_truck_pin_design(client):
    text = sheet(client, "map.css")
    assert ".pin svg{width:36px;height:54px}" in text
    assert ".pin .lbl" in text
    assert ".pin.sel .truck-svg" in text
    # Heading travels through a CSS variable; an inline transform would override
    # the selection scale declared in the sheet.
    assert ".pin .truck-svg{display:grid;transform:rotate(var(--heading,0deg))" in text


# --- login-map-ui (C2e): v10 chrome — collapsible sidebar ---

def test_map_sheet_keeps_the_collapsible_sidebar_geometry(client):
    text = sheet(client, "map.css")
    assert ".minibrand" in text
    assert ".app.nav-off" in text


# --- login-map-ui (C3): v10 glass dashboard layer ---

def test_map_sheet_keeps_the_v10_glass_fullscreen_layer(client):
    text = sheet(client, "map.css")
    assert "--g-bg:rgba(23,54,116,.72)" in text
    desktop_surfaces = text.split("@media (min-width:944px){", 1)[1]
    assert "--g-bg:rgba(255,255,255,.90)" in desktop_surfaces
    assert ".content,.grid,.grid>.col:first-child,.mapcard{display:contents}" in text
    assert ".mapbox{position:absolute;inset:0;z-index:0" in text
    assert ".side,.top,.card,.mapcard .card-h,.leaflet-bar,.leaflet-control-attribution" in text
    assert ".leaflet-top.leaflet-left{left:var(--lx);top:147px}" in text
    assert "@media (max-width:1265px)" in text


def test_map_sheet_keeps_the_mobile_view_switching_rules(client):
    text = sheet(client, "map.css")
    for view in ("panel", "fleet", "map"):
        assert f'body[data-mobile-view="{view}"]' in text


def test_map_sheet_keeps_the_mobile_glass_surfaces(client):
    text = sheet(client, "map.css")
    mobile_styles = text.split(
        "/* Mobile surfaces follow the supplied glass treatment without changing desktop. */",
        1,
    )[1]

    assert "@media (max-width:943px){" in mobile_styles
    assert "body{background:#f4f6fb" in mobile_styles
    assert 'body[data-mobile-view="panel"] .mapbox,body[data-mobile-view="fleet"] .mapbox{display:none}' in mobile_styles
    assert 'body[data-mobile-view="map"] .mapbox{display:block}' in mobile_styles
    assert "flex-wrap:nowrap" in mobile_styles
    assert ".search{flex:1 1 0%" in mobile_styles
    assert ".pill{flex:0 0 auto" in mobile_styles
    assert ".card:not(.mapcard),.side,.top{background:var(--g-bg)" in mobile_styles
    assert "-webkit-backdrop-filter:var(--blur);backdrop-filter:var(--blur)" in mobile_styles
    assert ".mobile-tabs{" in mobile_styles
    assert "background:var(--g-bg);-webkit-backdrop-filter:var(--blur);backdrop-filter:var(--blur)" in mobile_styles
    assert 'body[data-mobile-view="panel"] .mapcard .card-h,body[data-mobile-view="fleet"] .mapcard .card-h{display:none}' in mobile_styles
    assert 'body[data-mobile-view="map"] .mapcard .card-h{position:absolute' in mobile_styles
    assert ".side .logout{position:fixed" in mobile_styles
    assert ".leaflet-bar,.leaflet-control-attribution{background:var(--g-bg)" in mobile_styles
    assert ".leaflet-top.leaflet-left{left:auto;right:10px;top:10px}" in mobile_styles


# --- shared auth tokens ---

def test_auth_tokens_are_defined_once_for_both_pages(client):
    text = sheet(client, "auth-tokens.css")
    assert "--bg1:#dbe7f8" in text
    assert "--acc:#5a7ee6" in text
    assert "@media (prefers-color-scheme:dark)" in text


def test_login_keeps_its_own_status_color_and_meta_row(client):
    login = sheet(client, "login.css")
    assert ".meta{" in login
    assert ".status.ok{color:#f5f7f6}" in login


def test_register_keeps_the_create_join_mode_control(client):
    register = sheet(client, "register.css")
    assert ".mode{" in register
    assert ".mode button.active{background:var(--acc);color:#fff}" in register
