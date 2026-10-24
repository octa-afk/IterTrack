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
    assert re.search(r"\.pin\{[^}]*width:32px[^}]*height:62px", text)
    assert re.search(r"\.pin \.truck-img\{[^}]*width:32px[^}]*height:62px", text)
    assert ".pin .lbl" in text
    assert ".pin.sel .truck-img" in text
    assert "rotate(var(--heading,0deg))" in text
    # El marcador se achica al alejar el zoom; el JS publica --pin-scale y el
    # CSS lo compone con el rumbo (y la etiqueta sigue el tamaño escalado).
    assert "scale(var(--pin-scale,1))" in text
    assert re.search(r"\.pin \.lbl\{top:calc\(50% \+ 31px \* var\(--pin-scale,1\)", text)


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
    assert ".pin.off .truck-img{" in text
    assert re.search(r"\.detail \.trip\{[^}]*border-radius:12px", text)
    assert re.search(r"\.detail \.trip-st\{[^}]*grid-template-columns:repeat\(3,1fr\)", text)


@requires_build
def test_truck_marker_image_ships_inside_the_served_assets_directory():
    """El marcador debe vivir en /assets: FastAPI solo sirve esa carpeta.

    Un archivo en frontend/public llega al build como /truck.webp, que en
    producción responde 404 y deja el marcador como imagen rota.
    """
    assets = sorted((DIST / "assets").glob("*.webp"))
    assert assets, "the build emitted no marker image under assets/"
    assert assets[0].stat().st_size < 60_000, "the marker image is unoptimized"
    scripts = sorted((DIST / "assets").glob("*.js"))
    bundled = "".join(path.read_text(encoding="utf-8") for path in scripts)
    assert "/truck.webp" not in bundled


@requires_build
def test_mobile_layout_only_below_phone_widths():
    """La UI móvil no está curada: no debe aparecer al angostar una ventana de PC.

    El breakpoint tiene que quedar por debajo de una pantalla dividida típica
    (720-960 px); si sube, la demo en PC se convierte en la versión móvil.
    """
    text = built_css()
    assert "(width<=640px)" in text
    assert "(width>=641px)" in text
    assert "943px" not in text
    assert "944px" not in text
