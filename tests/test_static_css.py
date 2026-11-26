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
def test_selected_pin_label_is_deep_blue_with_white_text():
    """La patente del camión elegido se pinta en azul profundo con texto blanco.

    Es la única etiqueta visible en escritorio (`.pin .lbl` está oculta y sólo
    se muestra en `.pin.sel`), así que tiene que leerse como "este es el camión
    que estás mirando" y no confundirse con el azul de la ruta.
    """
    text = built_css()
    etiqueta = re.search(r"\.pin\.sel \.lbl\{([^}]*)\}", text)
    assert etiqueta, "the selected pin label rule is missing"
    regla = etiqueta.group(1)
    assert "background:var(--blue-deep)" in regla
    assert "color:#fff" in regla
    assert re.search(r"--blue-deep:#2b46a8", text)


@requires_build
def test_stop_pins_are_neutral_and_only_the_target_pulses():
    """Las paradas del viaje son negras; el destino se distingue por el halo.

    El color de las paradas competía con la ruta azul: se retiró el rojo de las
    pendientes y el gris de las entregadas (queda sólo la opacidad). La parada a
    la que va el camión lleva `target`, con un halo animado que se apaga con
    `prefers-reduced-motion`.
    """
    text = built_css()
    pin = re.search(r"\.stop-pin\{([^}]*)\}", text)
    assert pin and "background:#1f2a3d" in pin.group(1)
    assert not re.search(r"\.stop-pin\.pending\{", text)
    assert "stop-halo" in text
    # El minificador reescribe `::after` como `:after` y reordena las
    # propiedades: se busca la animación, no el texto exacto.
    target = re.search(r"\.stop-pin\.target:?:?after\{([^}]*)\}", text)
    assert target and "animation:" in target.group(1) and "stop-halo" in target.group(1)
    halo = re.search(r"@keyframes stop-halo\{(.*?)\}\}", text)
    assert halo and "scale(2.4)" in halo.group(1)


@requires_build
def test_dashboard_glass_layer():
    text = built_css()
    assert "--g-bg:#173674b8" in text  # rgba(23,54,116,.72)
    assert "--g-bg:#ffffffe6" in text  # rgba(255,255,255,.90)
    assert ".content,.grid,.grid>.col:first-child,.mapcard{display:contents}" in text
    assert re.search(r"\.mapbox\{[^}]*position:absolute[^}]*inset:0", text)
    # El estilo heredado de `data-mobile-view` ya no existe: el shell móvil
    # tiene sus propias clases `m-*` y no se activa por ancho.
    assert "data-mobile-view" not in text


@requires_build
def test_auth_styles_stay_scoped_to_the_auth_page():
    text = built_css()
    assert ".auth-page .side{" in text
    assert ".auth-page .logo{" in text
    assert ".auth-page .brand{" in text


@requires_build
def test_el_acceso_usa_sus_propios_estilos_acotados():
    """El login tiene hoja propia: no hereda de auth.css ni del dashboard.

    Anula el relleno que dashboard.css le pone al `body` y trae sus dos temas.
    """
    text = built_css()
    assert re.search(r"body:has\(\.login-page\)\{[^}]*padding:0", text)
    assert ".login-page .lg-card{" in text
    assert "prefers-color-scheme:dark" in text


@requires_build
def test_pastilla_del_mapa_con_logo_y_sin_tarjeta_flotante():
    """Sobre el mapa flotan la pastilla «Mapa en vivo» y el panel de flota.

    La pastilla lleva siempre el logo de IterTrack, con el lateral abierto o
    plegado. La tarjeta del camión ya no existe: su detalle se despliega dentro
    de la fila elegida (`.dc-embedded`).
    """
    text = built_css()
    logo = re.search(r"\.mapcard \.card-h \.map-mark\{([^}]*)\}", text)
    assert logo and "display:inline-flex" in logo.group(1)
    assert "truck-float" not in text
    assert re.search(r"\.listcard li\.sel\{[^}]*background", text)
    assert ".dc-embedded{" in text


@requires_build
def test_panel_de_flota_se_comprime_hacia_arriba():
    """Comprimido deja sólo la fila del buscador; el cuerpo crece hacia abajo.

    El panel está anclado arriba (`top:16px`), así que para comprimirlo hay que
    soltarle el `bottom` a la columna: si no, la tarjeta se queda con el alto
    completo y el buscador flota en un panel vacío.
    """
    text = built_css()
    cabecera = re.search(r"\.fleet-head\{([^}]*)\}", text)
    assert cabecera and "display:flex" in cabecera.group(1)
    assert re.search(r"\.fleet-collapse\{[^}]*cursor:pointer", text)
    # El cuerpo se apaga: `display:flex` le gana al `[hidden]` del navegador.
    assert re.search(r"\.listcard \.listcard-body\[hidden\]\{display:none\}", text)
    # Comprimido, la columna deja de estirarse hasta abajo.
    assert re.search(r":has\(\.listcard\.is-collapsed\)\{[^}]*bottom:auto", text)
    # El minificador escribe `flex:none`, que es exactamente `0 0 auto`.
    assert re.search(r"\.listcard\.is-collapsed\{[^}]*flex:(none|0 0 auto)", text)


@requires_build
def test_lateral_concentra_busqueda_y_perfil_sin_barra_superior():
    """La búsqueda y el perfil viven en el lateral, y los paneles arrancan arriba.

    Sin barra superior el mapa recupera esa franja: el encabezado del panel y la
    columna de flota empiezan a 16 px del borde, no a 97.
    """
    text = built_css()

    # El perfil y el contador de alertas son parte del lateral.
    assert re.search(r"\.side-head\{", text), "falta la cabecera del lateral"
    assert re.search(r"\.side-foot\{[^}]*margin:auto 16px", text), (
        "el pie con alertas y perfil no está dentro del lateral"
    )
    assert re.search(r"\.side-reopen\{", text), "falta el botón para reabrir el lateral"

    # La búsqueda no: vive en el panel de flota y en la tabla de Camiones, que
    # es donde se ve la flota que filtra.
    assert not re.search(r"\.side-search", text), "el buscador quedó en el lateral"
    assert re.search(r"\.fleet-search\{[^}]*display:flex", text)
    assert re.search(r"\.listcard \.fleet-search\{[^}]*margin-bottom:14px", text)
    assert re.search(r"\.fleetcard \.fleet-search\{", text)

    # Los paneles flotantes arrancan en el borde superior, no debajo de una barra.
    chip = re.search(r"\.mapcard \.card-h\{([^}]*)\}", text)
    assert chip and "top:16px" in chip.group(1)
    flota = re.search(r"\.grid>\.col:last-child\{([^}]*)\}", text)
    assert flota and "top:16px" in flota.group(1)


@requires_build
def test_fleet_panel_and_truck_panel_surfaces():
    text = built_css()
    # Panel de flota: cada unidad es una tarjeta con dot, patente y velocidad.
    assert re.search(r"\.listcard li button\{[^}]*grid-template-columns:10px", text)
    assert re.search(r"\.listcard \.sp\{[^}]*grid-(column:3|area:1/3)", text)
    # Panel del camión: grilla 2x2 de métricas y el resumen de la próxima parada.
    assert ".dc-tiles{" in text
    assert ".dc-tile{" in text
    assert ".dc-trip{" in text


@requires_build
def test_truck_active_state_and_trip_summary():
    text = built_css()
    assert ".badge-off{" in text
    assert ".pin.off .truck-img{" in text
    assert re.search(r"\.dc-trip .spark\{[^}]*height:56px", text)
    assert ".dc-trip-none{" in text


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
def test_mobile_design_is_scoped_to_the_mobile_shell():
    """El diseño de extras/mobile/itertrack vive sólo dentro de `.m-app`.

    El dashboard ya usa `.card`, `.nav` y `.count` con otro significado, así
    que la UI móvil se prefija con `m-`. El reset de botones usa `:where()`
    para no ganarle por especificidad al fondo de tarjetas y chips.
    """
    text = built_css()
    assert ".m-app{" in text
    assert re.search(r"\.m-app\{[^}]*--m-bg:#eef1f8", text)
    for selector in (".m-screen{", ".m-sheet{", ".m-drawer{", ".m-chip{"):
        assert selector in text
    assert ".m-app :where(button)" in text


@requires_build
def test_mobile_selected_pin_and_fleet_preview():
    """El pin elegido y la vista previa de la flota en la hoja del mapa.

    El pin seleccionado va pintado entero (fondo celeste, texto blanco), no
    blanco con marco. La hoja se despliega y se pliega con una transición de
    altura (`grid-template-rows` 0fr ↔ 1fr) sin cambiar de layout: si el
    contenedor cambiara de `display`, la misma transición correría a distinta
    velocidad en cada sentido. El cierre dura más que el despliegue y usa una
    curva en S (`cubic-bezier(.55, 0, .45, 1)` contra `cubic-bezier(.2, 0, 0, 1)`):
    arranca lento como la reproducción inversa, pero frena al llegar en vez de
    rematar de golpe.
    """
    text = built_css()
    label = re.search(r"\.m-app \.pin\.sel \.lbl\{([^}]*)\}", text)
    assert label, "the selected pin label rule is missing"
    # Azul profundo (no el acento claro) con texto blanco: es la etiqueta que
    # identifica al camión elegido sobre el mapa.
    assert "background:var(--m-accent-deep)" in label.group(1)
    assert "color:var(--m-surface)" in label.group(1)
    # La hoja se despliega y se pliega con la misma transición de altura.
    hoja = re.search(r"\.m-sheet__flota\{([^}]*)\}", text)
    assert hoja, "the fleet preview wrapper is missing"
    assert "grid-template-rows:0fr" in hoja.group(1)
    # El cierre arranca lento y frena al llegar: más largo que el despliegue.
    assert "transition:grid-template-rows .45s cubic-bezier(.55,0,.45,1)" in hoja.group(1)
    abierta = re.search(r"\.m-sheet__flota--open\{([^}]*)\}", text)
    assert abierta and "grid-template-rows:1fr" in abierta.group(1)
    assert "transition:grid-template-rows .33s cubic-bezier(.2,0,0,1)" in abierta.group(1)
    lista = re.search(r"\.m-flota-lista\{([^}]*)\}", text)
    assert lista and "overflow-y:auto" in lista.group(1)
    assert "transition:opacity .45s ease-in-out,transform .45s ease-in-out" in lista.group(1)
    abierta_lista = re.search(r"\.m-sheet__flota--open \.m-flota-lista\{([^}]*)\}", text)
    assert abierta_lista and "ease-out" in abierta_lista.group(1)


@requires_build
def test_mobile_map_screen_lets_gestures_reach_leaflet():
    """El panel del mapa no puede capturar los punteros.

    Es una capa transparente sobre el mapa: sin `pointer-events: none` se come
    el arrastre y el pellizco, y Leaflet nunca los ve. Sus controles flotantes
    (buscador, botones, hoja inferior) vuelven a habilitarlos por hijo.
    """
    text = built_css()
    screen = re.search(r"\.m-screen--map\{([^}]*)\}", text)
    assert screen, "the mobile map screen rule is missing"
    assert "pointer-events:none" in screen.group(1)
    assert re.search(r"\.m-screen--map>\*\{[^}]*pointer-events:auto", text)


@requires_build
def test_mobile_pinch_only_zooms_the_map():
    """Pellizcar sobre la UI no escala la página: sólo el mapa.

    `touch-action` vive en la capa de pantallas y en el drawer, nunca en
    `.m-app`: el navegador intersecta el valor con el de los ancestros, así que
    un `pan-x pan-y` arriba apagaría también el zoom táctil de Leaflet, que
    necesita su propio `touch-action: none`.
    """
    text = built_css()
    assert re.search(r"\.m-content,\.m-drawer\{[^}]*touch-action:pan-x pan-y", text), (
        "the mobile shell still lets the browser pinch-zoom the whole page"
    )
    shell = re.search(r"\.m-app\{[^}]*\}", text)
    assert shell and "touch-action" not in shell.group(0)


@requires_build
def test_mobile_layout_no_depende_del_ancho_de_la_ventana():
    """La UI móvil se elige por dispositivo, no por ancho de ventana.

    Achicar una ventana de PC tiene que dejar el dashboard con sus paneles
    flotantes sobre el mapa: ningún corte por ancho (640, 944 ni 1265 px) puede
    volver a apilar el lateral o a esconder la tarjeta del camión. El shell móvil
    se monta en `App.tsx` con `(hover: none) and (pointer: coarse)`.
    """
    text = built_css()
    for corte in ("640px", "641px", "943px", "944px", "1265px", "1266px"):
        assert corte not in text, f"quedó un corte de ancho en {corte}"
    app = (DIST.parent / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "(hover: none) and (pointer: coarse)" in app
    assert "max-width" not in app
