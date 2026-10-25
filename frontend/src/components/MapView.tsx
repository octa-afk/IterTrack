import { useEffect, useRef, useState } from 'react';
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

/* Largo de una polilínea, en metros. */
function largoGeometria(geometry: [number, number][]): number {
  let total = 0;
  for (let i = 1; i < geometry.length; i += 1) {
    total += haversineM(
      geometry[i - 1][0],
      geometry[i - 1][1],
      geometry[i][0],
      geometry[i][1],
    );
  }
  return total;
}

/*
 * Recorta la ruta en el punto más cercano al camión. OSRM devuelve la geometría
 * desde donde estaba el camión al pedirla; a los segundos ese origen queda atrás
 * y la línea arranca en una esquina que el camión ya pasó.
 */
function recortarRuta(
  geometry: [number, number][],
  lat: number,
  lng: number,
): { distancia: number; resto: [number, number][]; largo: number } {
  let indice = 0;
  let distancia = Number.POSITIVE_INFINITY;
  geometry.forEach(([aLat, aLng], i) => {
    const d = haversineM(lat, lng, aLat, aLng);
    if (d < distancia) {
      distancia = d;
      indice = i;
    }
  });
  const resto = geometry.slice(indice);
  return { distancia, resto, largo: distancia + largoGeometria(resto) };
}

/*
 * "12,4 km · 18 min": lo que el operador necesita para decidir, sin decimales de
 * más. Un viaje de menos de un minuto igual se informa como 1 min: redondear a 0
 * haría pensar que ya llegó.
 */
function describirRuta(distanceM: number, durationS: number): string {
  const km = (distanceM / 1000).toLocaleString('es-AR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  const minutos = Math.max(1, Math.round(durationS / 60));
  const tiempo =
    minutos < 60
      ? `${minutos} min`
      : `${Math.floor(minutos / 60)} h ${minutos % 60} min`;
  return `Ruta ${km} km · ${tiempo}`;
}

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

export default function MapView() {
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
  const trucksRef = useRef(trucks);
  const selectRef = useRef(select);
  const [routeSummary, setRouteSummary] = useState<{
    truckId: number;
    text: string;
  } | null>(null);

  useEffect(() => {
    trucksRef.current = trucks;
    selectRef.current = select;
  });

  /* Boot the Leaflet + MapLibre base map once. */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const map = L.map(el).setView(CITY_CENTER, OPEN_ZOOM);
    mapRef.current = map;
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
  }, []);

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
    let resumen = '';
    let proxima: TripStop | null = null;
    let ruta: {
      geometry: [number, number][];
      distance: number;
      duration: number;
      stopSeq: number;
      total: number;
    } | null = null;

    const mostrarResumen = (text: string) => {
      if (text === resumen) return;
      resumen = text;
      setRouteSummary({ truckId: selectedId, text });
    };

    const pintarParadas = (stops: TripStop[]) => {
      if (!tripRef.current) tripRef.current = L.layerGroup().addTo(map);
      const capa = tripRef.current;
      capa.clearLayers();
      proxima = null;
      for (const stop of stops) {
        if (stop.lat === null || stop.lng === null) continue;
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
        const clases = [
          'stop-pin',
          stop.needs_review ? 'pending' : '',
          entregada ? 'done' : '',
          enCurso ? 'here' : '',
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
              weight: 2,
              opacity: 0.7,
              dashArray: '7 6',
            },
          ).addTo(linea);
        }
        mostrarResumen('');
        return;
      }

      if (origen === null) {
        L.polyline(ruta.geometry, {
          color: '#3f6fe0',
          weight: 4,
          opacity: 0.85,
          lineJoin: 'round',
          lineCap: 'round',
        }).addTo(linea);
        mostrarResumen(
          `${describirRuta(ruta.distance, ruta.duration)} · parada ${ruta.stopSeq}`,
        );
        return;
      }

      const { distancia, resto, largo } = recortarRuta(
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
          weight: 4,
          opacity: 0.85,
          lineJoin: 'round',
          lineCap: 'round',
        }).addTo(linea);
      }
      const ratio = ruta.total > 0 ? Math.min(1, largo / ruta.total) : 1;
      mostrarResumen(
        `${describirRuta(ruta.distance * ratio, ruta.duration * ratio)} · parada ${ruta.stopSeq}`,
      );
    };

    const refrescar = async () => {
      const viajes = await listTrips(selectedId).catch(() => null);
      if (cancelado || viajes === null) return;
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
          mostrarResumen('');
        }
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

      const truck = trucksRef.current.find((t) => t.id === selectedId);
      const origen: [number, number] | null =
        truck && truck.lat !== null && truck.lng !== null
          ? [truck.lat, truck.lng]
          : null;

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
          nueva && nueva.geometry.length > 1
            ? {
                geometry: nueva.geometry,
                distance: nueva.distance_m,
                duration: nueva.duration_s,
                stopSeq: nueva.stop_seq,
                total: largoGeometria(nueva.geometry),
              }
            : null;
      }

      dibujarRuta(origen);
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

  /* Fly to the selected truck when the selection changes. */
  useEffect(() => {
    if (selectedId === null) return;
    const truck = trucksRef.current.find((t) => t.id === selectedId);
    const map = mapRef.current;
    if (!truck || truck.lat === null || truck.lng === null || !map) return;
    map.flyTo([truck.lat, truck.lng], Math.max(map.getZoom(), OPEN_ZOOM), {
      duration: 0.8,
    });
  }, [selectedId]);

  const resumenVisible =
    routeSummary && routeSummary.truckId === selectedId ? routeSummary.text : '';

  return (
    <>
      <div id="map" ref={containerRef} />
      {resumenVisible && (
        <span className="route-summary" aria-live="polite">
          {resumenVisible}
        </span>
      )}
    </>
  );
}
