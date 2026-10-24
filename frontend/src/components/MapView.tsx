import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import '@maplibre/maplibre-gl-leaflet';
import { listTrips } from '../api/destinations';
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
 * Azul cósmico para todos los recorridos. El trazado es el mismo para cualquier
 * camión y se mira de a uno, así que el color no tiene que distinguir la flota.
 */
const TRAIL_COLOR = '#1f3a93';

/*
 * Escala del marcador según el zoom. A zoom ciudad (12+) se dibuja a tamaño
 * completo; alejándose se achica hasta 55% para no tapar la provincia entera.
 * Nunca escala por encima de 1: crecer al acercarse solo tapa las calles.
 */
const PIN_FULL_ZOOM = OPEN_ZOOM;
const PIN_MIN_SCALE = 0.55;
const PIN_SCALE_PER_ZOOM = 0.09;

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
  const { trucks, visibleTrucks, selectedId, select } = useDashboard();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef(new Map<number, L.Marker>());
  const lastPosRef = useRef(new Map<number, { lat: number; lng: number; updated: number }>());
  const movesRef = useRef(new Map<number, ActiveMove>());
  const movementRef = useRef<ReturnType<typeof createMovementController> | null>(null);
  const trailRef = useRef<L.LayerGroup | null>(null);
  const tripRef = useRef<L.LayerGroup | null>(null);
  const fittedRef = useRef(false);
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
   * Draw the selected truck's recent trail under the markers. Se dibuja sólo el
   * último tramo continuo (ver `splitPath`): el recorrido de una corrida
   * anterior —simulador reiniciado, camión que cambió de ruta, GPS que saltó—
   * no es el recorrido actual, y unirlo dibuja calles que el camión no hizo.
   */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const truck = trucks.find((t) => t.id === selectedId);
    const tramos = truck ? splitPath(truck.path) : [];
    const actual = tramos[tramos.length - 1];

    if (!truck || !actual) {
      trailRef.current?.remove();
      trailRef.current = null;
      tripRef.current?.remove();
      tripRef.current = null;
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
  }, [trucks, selectedId]);

  /*
   * Destinos del viaje abierto del camión seleccionado. Es el único trabajo que
   * no está en el polling de la flota: los viajes cambian por decisiones
   * humanas, así que se piden al cambiar la selección.
   */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (selectedId === null) {
      tripRef.current?.clearLayers();
      return;
    }

    let cancelado = false;
    void (async () => {
      const viajes = await listTrips(selectedId).catch(() => []);
      if (cancelado) return;
      const activo = viajes.find(
        (viaje) => viaje.status === 'planned' || viaje.status === 'in_progress',
      );
      if (!tripRef.current) tripRef.current = L.layerGroup().addTo(map);
      const capa = tripRef.current;
      capa.clearLayers();
      if (!activo) return;

      const puntos: [number, number][] = [];
      for (const stop of activo.stops) {
        if (stop.lat === null || stop.lng === null) continue;
        puntos.push([stop.lat, stop.lng]);
        L.marker([stop.lat, stop.lng], {
          icon: L.divIcon({
            className: '',
            iconSize: [22, 22],
            iconAnchor: [11, 11],
            html: `<span class="stop-pin${stop.needs_review ? ' pending' : ''}">${stop.seq}</span>`,
          }),
          title: stop.address,
        }).addTo(capa);
      }
      if (puntos.length > 1) {
        L.polyline(puntos, {
          color: '#3f6fe0',
          weight: 2,
          opacity: 0.7,
          dashArray: '7 6',
        }).addTo(capa);
      }
    })();

    return () => {
      cancelado = true;
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

  return <div id="map" ref={containerRef} />;
}
