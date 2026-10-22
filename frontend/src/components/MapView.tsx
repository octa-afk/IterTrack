import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import '@maplibre/maplibre-gl-leaflet';
import { useDashboard } from '../state/useDashboard';
import { createTruckIcon } from '../lib/truckIcon';
import { createMovementController, type ActiveMove } from '../lib/movement';
import { POLL_MS, haversineM } from '../lib/trucks';

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

    const map = L.map(el).setView([-31.9, -64.0], 7);
    mapRef.current = map;
    const markers = markersRef.current;
    const lastPos = lastPosRef.current;
    const moves = movesRef.current;
    el.classList.add('map-style-loading');

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
      markers.clear();
      lastPos.clear();
      moves.clear();
      map.remove();
      mapRef.current = null;
    };
  }, []);

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
