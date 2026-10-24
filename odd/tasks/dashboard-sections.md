# Secciones del dashboard

Objetivo: convertir el sidebar en navegación real y darle páginas propias a las
secciones de la flota, empezando por Camiones.
Rama: `feat/dashboard-original` · Entrega: commits por unidad de trabajo · Tests: `make test` + `npm --prefix frontend run lint build`

## Specs

S1. Las cinco entradas del sidebar (`Panel`, `Camiones`, `Rutas`, `Reportes`,
`Ajustes`) deben navegar a una ruta propia. Hoy son `<a>` sin `href` que no
hacen nada.

S2. `Camiones` tiene página propia en `/trucks` con la flota completa en tabla:
patente, estado, velocidad, último reporte y rumbo. Reutiliza el estado y los
filtros que ya existen (búsqueda, estado, orden) en lugar de crear otro store.

S3. El estado de la flota (polling cada 3 s, selección, filtros) vive en un
layout compartido, de modo que cambiar de sección no reinicia el polling ni
pierde el camión seleccionado.

S4. FastAPI sirve `index.html` en las rutas nuevas: un *deep link* directo a
`/trucks` no puede devolver `404`.

S5. `Rutas`, `Reportes` y `Ajustes` **no** entran en esta entrega y eso se
declara: se muestran deshabilitadas con `title="Próximamente"`, sin páginas
falsas ni contenido inventado.

S7. El mapa no se recrea al cambiar de sección: se monta una vez y se oculta
mientras no estás en el panel.

S6. `extras/nuevo html(prueba)` **no** se usa como referencia de diseño: es
material local de otra rama, ignorado por git. Borrarlo queda a decisión del
usuario porque no está respaldado en ninguna rama.

## Tasks

| ID | Specs | Ruta | Estado |
|----|-------|------|--------|
| T1 | S1, S3, S4 | inline | hecho |
| T2 | S2 | inline | hecho |
| T3 | S5 | inline | hecho |
| T4 | docs | inline | hecho |

## Log

L1 (2026-10-24, textual): "quiero que sigamos implementando el resto del
frontend, quiero agregar mas secciones"

L2 (2026-10-24, textual): "no veamoes el archivo html de prueba, es de otra
branch, si queres inclusive borralo de esta branch para no geenrera confusiones"

L3: `extras/` está en `.gitignore:26` y no existe en `develop`, `main` ni
`feat/dashboard-redesign-nuevo`. No se borra: no afecta al repo y su pérdida
sería local y definitiva. Se deja constancia en S6.

L4: hallazgo de exploración — `source/main.py` registra `/`, `/register` y
`/map` una por una, y `tests/test_static.py` las parametriza. Toda ruta nueva
del cliente exige registrar el handler y sumarla al test, o el deep link da 404.

L5: T1 y T2 implementados. Hallazgos de implementación:
- `.grid` no sirve para páginas normales: el layer "full-screen map" le aplica
  `display:contents` a `.grid`, `.content` y `.grid>.col:first-child`, así que
  una tarjeta metida ahí cae en la columna del sidebar (253 px) y queda tapada.
  La sección usa `.fleet-page`, con la misma geometría que los paneles
  flotantes (`top:97px`, `bottom:39px`, `left:var(--lx)`) y fallback a flujo
  normal por debajo de 1265 px.
- `/trucks` colisiona con `GET /trucks` de la API (401 JSON). De ahí `/fleet`.
- El ancho útil a 1280 px es 527 px: la etiqueta "Ver en el mapa" se cortaba.
  Quedó "Ver mapa" + `aria-label` con la patente, y celdas a 10 px.
Verificación: `/fleet` 200 HTML y `/trucks` 401 JSON, tabla con 3 filas,
selección de fila poblando el detalle, "Ver mapa" navegando a `/map` con los
3 marcadores, `make check` y `make test` (199) en verde.

L6 (pedido del usuario, textual): "veo que al pasar a la seccion de camiones y
volver al panel principal tarda en cargar el mapa, y no es un problema de
rendimiento de mi pc. como podemos solucionarlo?"

L7: causa medida, no supuesta. Con el mapa en `MapPage`, al navegar a `/fleet`
`#map` desaparecía del DOM: `MapView` se desmontaba y en cada vuelta se creaban
otra vez `L.map()` y la capa de MapLibre, se pedía y parseaba el estilo de
OpenFreeMap y se rearmaban los tres marcadores. El overlay `.map-style-loading`
volvía a tapar el panel mientras tanto.
Solución (S7): el mapa pasa a `DashboardLayout` y se monta una sola vez; fuera
del panel se oculta con `.mapbox-off` — `visibility:hidden` en escritorio para
no cambiar el tamaño (Leaflet no necesita `invalidateSize`) y `display:none`
por debajo de 1265 px, donde el mapa está en flujo normal y no debe dejar un
hueco de 64vh.
Verificación: tras /map → /fleet → /map el nodo `#map` y el `<canvas>` son los
mismos objetos (`===`), `.mapbox` está `hidden` en flota y sin `map-style-loading`
al volver; 3 marcadores presentes. A 1024 px el mapa oculto no ocupa alto.
Bug menor encontrado en la tabla: el rumbo salía crudo (225.44311469526514°)
porque `bearing()` devuelve float y sólo `TruckDetail` redondeaba.
