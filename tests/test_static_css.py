"""Design regressions in the shipped CSS bundle.

The vanilla stylesheets were retired in T12, so the design intent is asserted
against the hashed CSS that Vite emits (what the browser actually loads).
Property order is minifier-dependent, so structural rules use regexes.
"""

import re
from pathlib import Path

import pytest

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
requires_build = pytest.mark.skipif(
    not (DIST / "assets").is_dir(),
    reason="frontend build missing; run: npm --prefix frontend run build",
)


def built_css() -> str:
    files = sorted((DIST / "assets").glob("*.css"))
    assert files, "the build emitted no CSS bundle"
    return "".join(path.read_text(encoding="utf-8") for path in files)


@requires_build
def test_pin_geometry_and_heading_rotation():
    text = built_css()
    assert ".pin svg{width:36px;height:54px}" in text
    assert ".pin .lbl" in text
    assert ".pin.sel .truck-svg" in text
    assert "rotate(var(--heading,0deg))" in text


@requires_build
def test_dashboard_glass_layer():
    text = built_css()
    assert "--g-bg:#173674b8" in text  # rgba(23,54,116,.72)
    assert "--g-bg:#ffffffe6" in text  # rgba(255,255,255,.90)
    assert ".content,.grid,.grid>.col:first-child,.mapcard{display:contents}" in text
    assert re.search(r"\.mapbox\{[^}]*position:absolute[^}]*inset:0", text)
    for view in ("panel", "fleet", "map"):
        assert f"data-mobile-view={view}]" in text


@requires_build
def test_auth_styles_stay_scoped_to_the_auth_page():
    text = built_css()
    assert ".auth-page .side{" in text
    assert ".auth-page .logo{" in text
    assert ".auth-page .brand{" in text


@requires_build
def test_bottom_cards_surfaces():
    text = built_css()
    assert ".bars{" in text
    assert ".bar{" in text
    assert ".donuts{" in text


@requires_build
def test_truck_active_state_and_trip_summary():
    text = built_css()
    assert ".badge-off{" in text
    assert ".pin.off .truck-svg{" in text
    assert re.search(r"\.detail \.trip\{[^}]*border-radius:12px", text)
    assert re.search(r"\.detail \.trip-st\{[^}]*grid-template-columns:repeat\(3,1fr\)", text)
