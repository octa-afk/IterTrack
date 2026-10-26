import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import '@maplibre/maplibre-gl-leaflet';
import { getTripRoute, listTrips } from '../api/destinations';
import type { TripStop } from '../api/types';
import { useDashboard } from '../state/useDashboard';
import { createTruckIcon } from '../lib/truckIcon';
import { createMovementController, type ActiveMove } from '../lib/movement';
import { POLL_MS, haversineM, splitPath } from '../lib/trucks';
import { recortarRuta } from '../lib/route';

/*
 * Ported from source/static/js/map.js (map boot + marker rendering) plus
 * truck-marker.js and truck-movement.js.
 */
const MAP_STYLE = 'https://tiles.openfreemap.org/styles/bright';
const ATTRIBUTION =
  '<a href="https://openfreemap.org">OpenFreeMap</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const MOVE_MIN_MS = 400;
const MOVE_MAX_MS = 6000;
const MOVE_EASE = (k: number) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2);
const OPEN_ZOOM = 12;
/* Córdoba Capital: encuadre inicial antes de ajustar a la flota. */
const CITY_CENTER: [number, number] = [-31.4135, -64.1811];
/*
 * Rojo para el recorrido hecho: el azul cósmico queda para la ruta que falta y
 * el trazo ya recorrido no se confunde con ella.
 */
const TRAIL_COLOR = '#d64545';

/*
 * Escala del marcador según el zoom. A zoom ciudad (12+) se dibuja a tamaño
 * completo; alejándose se achica hasta 55% para no tapar la provincia entera.
 * Nunca escala por encima de 1: crecer al acercarse solo tapa las calles.
 */
const PIN_FULL_ZOOM = OPEN_ZOOM;
const PIN_MIN_SCALE = 0.55;
const PIN_SCALE_PER_ZOOM = 0.09;
/*
 * Cuánto se puede alejar el camión de la ruta pedida antes de volver a pedirla.
 * Mientras siga cerca, la línea se recorta en su posición y no se gasta una
 * consulta a OSRM por cada latido.
 */
const DESVIO_MAX_M = 120;

/* Grosor de la ruta hasta la próxima parada. La recta de respaldo (sin
 * proveedor de ruteo) va dos píxeles más fina para no leerse como calle. */
const ROUTE_WEIGHT = 6;

function pinScale(zoom: number): number {
  const raw = 1 - (PIN_FULL_ZOOM - zoom) * PIN_SCALE_PER_ZOOM;
  return Math.min(1, Math.max(PIN_MIN_SCALE, raw));
}

type MaplibreLayer = L.Layer & { getMaplibreMap(): maplibregl.Map };
type MaplibreFactory = (options: {
  style: string;
  attribution?: string;
}) => MaplibreLayer;

const maplibreGL = (L as unknown as { maplibreGL: MaplibreFactory }).maplibreGL;

interface MapViewProps {
  /**
   * Entrega el mapa ya creado. La UI móvil lo necesita para sus propios
   * controles de zoom y ubicación; el escritorio usa el control de Leaflet.
   */
  onReady?: (map: L.Map) => void;
  /** Oculta el control de zoom de Leaflet (la UI móvil dibuja el suyo). */
  showZoomControl?: boolean;
  /**
   * Al elegir un camión, encuadra la vista sobre él **y** su viaje abierto
   * (paradas que faltan y ruta hasta la próxima). El escritorio conserva el
   * vuelo al camión: ahí el panel lateral deja ver el contexto.
   */
  fitSelection?: boolean;
}

export default function MapView({
  onReady,
  showZoomControl = true,
  fitSelection = false,
}: MapViewProps = {}) {
  const { trucks, visibleTrucks, selectedId, recorridoId, select } = useDashboard();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef(new Map<number, L.Marker>());
  const lastPosRef = useRef(new Map<number, { lat: number; lng: number; updated: number }>());
  const movesRef = useRef(new Map<number, ActiveMove>());
  const movementRef = useRef<ReturnType<typeof createMovementController> | null>(null);
  const trailRef = useRef<L.LayerGroup | null>(null);
  const tripRef = useRef<L.LayerGroup | null>(null);
  const routeRef = useRef<L.LayerGroup | null>(null);
  const fittedRef = useRef(false);
  /* Pedido de encuadre pendiente: se resuelve cuando llegan las paradas. */
  const fitPendingRef = useRef(false);
  const trucksRef = useRef(trucks);
  const selectRef = useRef(select);

  useEffect(() => {
    trucksRef.current = trucks;
    selectRef.current = select;
  });

  /* Boot the Leaflet + MapLibre base map once. */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const map = L.map(el, { zoomControl: showZoomControl }).setView(
      CITY_CENTER,
      OPEN_ZOOM,
    );
    mapRef.current = map;
    onReady?.(map);
    const markers = markersRef.current;
    const lastPos = lastPosRef.current;
    const moves = movesRef.current;
    el.classList.add('map-style-loading');

    /* El tamaño del marcador vive en CSS: acá solo publicamos la escala. */
    const applyPinScale = () => {
      el.style.setProperty('--pin-scale', String(pinScale(map.getZoom())));
    };
    applyPinScale();
    map.on('zoomend', applyPinScale);

    const base = maplibreGL({ style: MAP_STYLE, attribution: ATTRIBUTION });
    base.addTo(map);
    const lib = base.getMaplibreMap();

    const originalRoadLineColors = new Map<string, string | undefined>();
    let showColoredRoads = false;

    const applyRoadColorMode = () => {
      if (!lib.isStyleLoaded()) return;
      lib.getStyle().layers.forEach((layer) => {
        const sourceLayer = (layer as { 'source-layer'?: string })['source-layer'] || '';
        const isRoadLine =
          layer.type === 'line' &&
          sourceLayer === 'transportation' &&
          /^(highway|bridge|tunnel)-/.test(layer.id);
        if (!isRoadLine) return;
        if (!originalRoadLineColors.has(layer.id)) {
          originalRoadLineColors.set(
            layer.id,
            (layer.paint as Record<string, unknown> | undefined)?.['line-color'] as
              | string
              | undefined,
          );
        }
        const originalColor = originalRoadLineColors.get(layer.id);
        if (originalColor === undefined) return;
        const color = showColoredRoads
          ? originalColor
          : layer.id.endsWith('-casing')
            ? '#b9c1cc'
            : '#e2e6ec';
        lib.setPaintProperty(layer.id, 'line-color', color);
      });
    };

    const neutralizeBuildings = () => {
      if (!lib.isStyleLoaded()) return;
      lib.getStyle().layers.forEach((layer) => {
        const sourceLayer = (layer as { 'source-layer'?: string })['source-layer'] || '';
        if (layer.type === 'fill' && sourceLayer === 'building') {
          lib.setPaintProperty(layer.id, 'fill-opacity', 0);
        } else if (layer.type === 'fill-extrusion' && sourceLayer === 'building') {
          lib.setPaintProperty(layer.id, 'fill-extrusion-opacity', 0);
        }
      });
      applyRoadColorMode();
    };

    const mostrarCargaEstilo = () => el.classList.add('map-style-loading');
    const ocultarCargaEstilo = () => el.classList.remove('map-style-loading');
    const mapaListo = () => {
      neutralizeBuildings();
      ocultarCargaEstilo();
    };

    lib.on('styledataloading', mostrarCargaEstilo);
    lib.on('load', mapaListo);
    lib.on('style.load', neutralizeBuildings);
    lib.on('error', ocultarCargaEstilo);

    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target;
      const isEditing =
        target instanceof HTMLElement &&
        (target.isContentEditable ||
          ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName));
      if (
        !window.matchMedia('(min-width: 944px)').matches ||
        isEditing ||
        event.repeat ||
        event.ctrlKey ||
        event.metaKey ||
        !event.altKey ||
        !event.shiftKey ||
        event.code !== 'KeyR'
      ) {
        return;
      }
      event.preventDefault();
      showColoredRoads = !showColoredRoads;
      applyRoadColorMode();
    };
    document.addEventListener('keydown', onKeyDown);

    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(el);

    movementRef.current = createMovementController({
      moves,
      markers,
      minDuration: MOVE_MIN_MS,
      maxDuration: MOVE_MAX_MS,
      defaultDuration: POLL_MS,
      ease: MOVE_EASE,
      distance: haversineM,
    });

    return () => {
      observer.disconnect();
      document.removeEventListener('keydown', onKeyDown);
      movementRef.current?.stop();
      movementRef.current = null;
      trailRef.current?.remove();
      trailRef.current = null;
      tripRef.current?.remove();
      tripRef.current = null;
      routeRef.current?.remove();
      routeRef.current = null;
      markers.clear();
      lastPos.clear();
      moves.clear();
      map.remove();
      mapRef.current = null;
    };
  }, [onReady, showZoomControl]);

  /*
   * Encuadre inicial: al recargar, el mapa se abre sobre la flota con el zoom
   * justo para ver los tres camiones, no en la provincia entera. Se hace una
   * sola vez; después manda la selección.
   */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || fittedRef.current || selectedId !== null) return;
    const puntos = trucks
      .filter((truck) => truck.lat !== null && truck.lng !== null)
      .map((truck) => [truck.lat as number, truck.lng as number] as [number, number]);
    if (!puntos.length) return;
    fittedRef.current = true;
    map.fitBounds(L.latLngBounds(puntos), { padding: [70, 70], maxZoom: OPEN_ZOOM });
  }, [trucks, selectedId]);

  /* Reconcile markers with the current fleet state. */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const visibleIds = new Set(visibleTrucks.map((truck) => truck.id));
    const liveIds = new Set<number>();

    for (const truck of trucks) {
      if (truck.lat === null || truck.lng === null) continue;
      liveIds.add(truck.id);

      let marker = markersRef.current.get(truck.id);
      if (!marker) {
        marker = L.marker([truck.lat, truck.lng], {
          icon: createTruckIcon(truck, false),
          title: truck.plate,
        });
        marker.on('click', () => selectRef.current(truck.id));
        markersRef.current.set(truck.id, marker);
      }

      const previous = lastPosRef.current.get(truck.id);
      if (previous) {
        const moved = haversineM(previous.lat, previous.lng, truck.lat, truck.lng);
        if (moved >= 5) {
          movementRef.current?.programarMovimiento(
            truck,
            [previous.lat, previous.lng],
            [truck.lat, truck.lng],
            truck.updated - previous.updated,
          );
        } else if (!movesRef.current.has(truck.id)) {
          marker.setLatLng([truck.lat, truck.lng]);
        }
      } else if (!movesRef.current.has(truck.id)) {
        marker.setLatLng([truck.lat, truck.lng]);
      }
      lastPosRef.current.set(truck.id, {
        lat: truck.lat,
        lng: truck.lng,
        updated: truck.updated,
      });

      marker.setIcon(createTruckIcon(truck, truck.id === selectedId));
      if (visibleIds.has(truck.id)) {
        if (!map.hasLayer(marker)) marker.addTo(map);
      } else {
        map.removeLayer(marker);
      }
    }

    for (const [id, marker] of markersRef.current) {
      if (liveIds.has(id)) continue;
      map.removeLayer(marker);
      markersRef.current.delete(id);
      lastPosRef.current.delete(id);
      movesRef.current.delete(id);
    }
  }, [trucks, visibleTrucks, selectedId]);

  /*
   * Recorrido hecho del camión seleccionado. No se dibuja por defecto: el mapa
   * principal muestra sólo lo que falta (la ruta por hacer). Se enciende cuando
   * el operador lo pide desde Rutas con `verRecorrido`.
   *
   * Se dibuja sólo el último tramo continuo (ver `splitPath`): el recorrido de
   * una corrida anterior —simulador reiniciado, camión que cambió de ruta, GPS
   * que saltó— no es el recorrido actual, y unirlo dibuja calles que el camión
   * no hizo.
   */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const truck = trucks.find((t) => t.id === selectedId);
    const tramos = truck ? splitPath(truck.path) : [];
    const actual = tramos[tramos.length - 1];

    if (!truck || !actual || truck.id !== recorridoId) {
      trailRef.current?.remove();
      trailRef.current = null;
      return;
    }

    if (!trailRef.current) trailRef.current = L.layerGroup().addTo(map);
    const capa = trailRef.current;
    capa.clearLayers();
    L.polyline(
      actual.map((point) => [point.lat, point.lng] as [number, number]),
      {
        color: TRAIL_COLOR,
        weight: 4,
        opacity: 0.9,
        lineJoin: 'round',
        lineCap: 'round',
      },
    ).addTo(capa);

    /* Dónde empezó la corrida que se está mirando. */
    const inicio = actual[0];
    L.circleMarker([inicio.lat, inicio.lng], {
      radius: 5,
      color: '#fff',
      weight: 2,
      fillColor: TRAIL_COLOR,
      fillOpacity: 1,
    })
      .bindTooltip('Inicio del recorrido')
      .addTo(capa);
  }, [trucks, selectedId, recorridoId]);

  /*
   * Destinos y progreso del viaje abierto del camión seleccionado. Se refresca
   * con el mismo latido de la flota: cuando el camión entrega una parada, el pin
   * pasa a hecho y la ruta apunta a la siguiente sin reseleccionar.
   *
   * La línea se recorta en la posición actual del camión en cada latido (no hace
   * falta otra consulta) y sólo se vuelve a pedir la ruta a OSRM cuando cambia
   * la parada destino o el camión se alejó de la ruta dibujada.
   */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (selectedId === null) {
      tripRef.current?.clearLayers();
      routeRef.current?.clearLayers();
      return;
    }

    let cancelado = false;
    let estadoRuta = '';
    let pedida = false;
    let proxima: TripStop | null = null;
    let ruta: { geometry: [number, number][] } | null = null;
    /* Paradas dibujadas, para encuadrar la vista sobre el viaje abierto. */
    let puntosParadas: [number, number][] = [];

    const pintarParadas = (stops: TripStop[]) => {
      if (!tripRef.current) tripRef.current = L.layerGroup().addTo(map);
      const capa = tripRef.current;
      capa.clearLayers();
      proxima = null;
      puntosParadas = [];
      for (const stop of stops) {
        if (stop.lat === null || stop.lng === null) continue;
        puntosParadas.push([stop.lat, stop.lng]);
        /*
         * El estado de la parada se ve en el pin: el número es el orden del
         * viaje, el check una parada ya entregada y el aro la que se está
         * visitando ahora. Sin esto el operador ve el número 1 al lado de una
         * ruta que va a la 3 y cree que el viaje se salteó una parada.
         */
        const entregada = stop.status === 'delivered';
        const enCurso = stop.status === 'arrived';
        if (!proxima && stop.status === 'pending') {
          proxima = stop;
        }
        /*
         * La parada destino —la primera `pending`— lleva el halo que late: es
         * a la que apunta la ruta, y sin él el número azul se confundía con
         * las demás. Una parada `arrived` ya se está visitando y no compite.
         */
        const esDestino = !proxima && stop.status === 'pending';
        const clases = [
          'stop-pin',
          stop.needs_review ? 'pending' : '',
          entregada ? 'done' : '',
          enCurso ? 'here' : '',
          esDestino ? 'target' : '',
        ]
          .filter(Boolean)
          .join(' ');
        L.marker([stop.lat, stop.lng], {
          icon: L.divIcon({
            className: '',
            iconSize: [22, 22],
            iconAnchor: [11, 11],
            html: `<span class="${clases}">${entregada ? '✓' : stop.seq}</span>`,
          }),
          title: `Parada ${stop.seq}${entregada ? ' · entregada' : enCurso ? ' · en curso' : ''} — ${stop.address}`,
        }).addTo(capa);
      }
    };

    const dibujarRuta = (origen: [number, number] | null) => {
      if (!routeRef.current) routeRef.current = L.layerGroup().addTo(map);
      const linea = routeRef.current;
      linea.clearLayers();
      if (!ruta) {
        // Sin proveedor configurado —o con el proveedor caído— queda la recta
        // punteada hasta la parada que toca: nunca se queda sin ver el destino.
        if (
          origen !== null &&
          proxima !== null &&
          proxima.lat !== null &&
          proxima.lng !== null
        ) {
          L.polyline(
            [origen, [proxima.lat, proxima.lng]],
            {
              color: '#3f6fe0',
              weight: ROUTE_WEIGHT - 2,
              opacity: 0.85,
              dashArray: '9 7',
            },
          ).addTo(linea);
        }
        return;
      }

      if (origen === null) {
        L.polyline(ruta.geometry, {
          color: '#3f6fe0',
          weight: ROUTE_WEIGHT,
          opacity: 0.9,
          lineJoin: 'round',
          lineCap: 'round',
        }).addTo(linea);
        return;
      }

      const { distancia, resto } = recortarRuta(
        ruta.geometry,
        origen[0],
        origen[1],
      );
      // El tramo arranca en el camión: si está a metros de la ruta, se une con
      // una recta corta en vez de dejar un hueco.
      const puntos: [number, number][] = distancia > 5 ? [origen, ...resto] : resto;
      if (puntos.length > 1) {
        L.polyline(puntos, {
          color: '#3f6fe0',
          weight: ROUTE_WEIGHT,
          opacity: 0.9,
          lineJoin: 'round',
          lineCap: 'round',
        }).addTo(linea);
      }
    };

    /*
     * Encuadre de la selección en móvil: camión + paradas del viaje abierto.
     * Se resuelve acá y no al tocar el pin porque las paradas llegan después
     * de la consulta de viajes; con una sola coordenada —sin viaje abierto o
     * sin proveedor de ruteo— se vuela al camión como en escritorio.
     */
    const encuadrar = (origen: [number, number] | null) => {
      const map = mapRef.current;
      if (!map || !fitPendingRef.current) return;
      fitPendingRef.current = false;

      const puntos: [number, number][] = origen ? [origen] : [];
      for (const punto of puntosParadas) puntos.push(punto);
      if (!puntos.length) return;

      if (puntos.length === 1) {
        const zoom = map.getZoom();
        map.flyTo(puntos[0], Math.max(Number.isFinite(zoom) ? zoom : OPEN_ZOOM, 13), {
          duration: 0.8,
        });
        return;
      }

      /* La hoja inferior y el buscador son parte fija de la pantalla móvil:
       * el encuadre les deja el lugar para que ninguna parada quede tapada. */
      map.fitBounds(L.latLngBounds(puntos), {
        paddingTopLeft: [24, 96],
        paddingBottomRight: [24, 240],
        maxZoom: 15,
        duration: 0.6,
      });
    };

    const refrescar = async () => {
      const truck = trucksRef.current.find((t) => t.id === selectedId);
      const origen: [number, number] | null =
        truck && truck.lat !== null && truck.lng !== null
          ? [truck.lat, truck.lng]
          : null;

      const viajes = await listTrips(selectedId).catch(() => null);
      if (cancelado || viajes === null) {
        encuadrar(origen);
        return;
      }
      const activo = viajes.find(
        (viaje) => viaje.status === 'planned' || viaje.status === 'in_progress',
      );

      if (!activo) {
        if (estadoRuta !== '') {
          tripRef.current?.clearLayers();
          routeRef.current?.clearLayers();
          estadoRuta = '';
          pedida = false;
          ruta = null;
        }
        encuadrar(origen);
        return;
      }

      // El estado de las paradas es lo único que cambia a qué parada apunta la
      // ruta, así que su firma decide si hay que repintar y volver a pedirla.
      const estado = activo.stops.map((stop) => stop.status).join('');
      if (estado !== estadoRuta) {
        estadoRuta = estado;
        pintarParadas(activo.stops);
        pedida = false;
        ruta = null;
        routeRef.current?.clearLayers();
      }

      const desvio =
        ruta !== null && origen !== null
          ? recortarRuta(ruta.geometry, origen[0], origen[1]).distancia
          : Number.POSITIVE_INFINITY;
      const hayQuePedir = !pedida || (ruta !== null && desvio > DESVIO_MAX_M);

      if (hayQuePedir) {
        pedida = true;
        /*
         * Ruta por calles hasta la parada que toca. Sin proveedor configurado —o
         * con el proveedor caído— queda la recta punteada hasta esa misma
         * parada: el operador nunca se queda sin ver a dónde tiene que ir.
         */
        const nueva = await getTripRoute(activo.id).catch(() => null);
        if (cancelado) return;
        ruta =
          nueva && nueva.geometry.length > 1 ? { geometry: nueva.geometry } : null;
      }

      dibujarRuta(origen);
      encuadrar(origen);
    };

    void refrescar();
    const interval = window.setInterval(() => {
      void refrescar();
    }, POLL_MS);

    return () => {
      cancelado = true;
      window.clearInterval(interval);
    };
  }, [selectedId]);

  /*
   * Fly to the selected truck when the selection changes. El mapa puede estar
   * oculto (el shell móvil lo monta también en las secciones sin mapa y lo
   * muestra con `display:none`): con tamaño cero o zoom indefinido, `flyTo`
   * proyecta NaN y tumba la app. En ese caso se deja la vista como está.
   */
  useEffect(() => {
    if (selectedId === null) {
      fitPendingRef.current = false;
      return;
    }
    if (fitSelection) {
      /* El encuadre necesita las paradas del viaje abierto: lo hace `refrescar`. */
      fitPendingRef.current = true;
      return;
    }
    const truck = trucksRef.current.find((t) => t.id === selectedId);
    const map = mapRef.current;
    if (!truck || truck.lat === null || truck.lng === null || !map) return;
    if (!Number.isFinite(truck.lat) || !Number.isFinite(truck.lng)) return;
    const size = map.getSize();
    if (size.x === 0 || size.y === 0) return;
    const currentZoom = map.getZoom();
    const zoom = Math.max(Number.isFinite(currentZoom) ? currentZoom : OPEN_ZOOM, OPEN_ZOOM);
    map.flyTo([truck.lat, truck.lng], zoom, { duration: 0.8 });
  }, [selectedId, fitSelection]);

  return (
    <>
      <div id="map" ref={containerRef} />
    </>
  );
}
