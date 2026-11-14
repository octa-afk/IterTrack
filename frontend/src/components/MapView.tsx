import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import '@maplibre/maplibre-gl-leaflet';
import type { Trip, TripStop } from '../api/types';
import { useDashboard } from '../state/useDashboard';
import { createTruckPin, updateTruckPin, type TruckPin } from '../lib/truckIcon';
import { createMovementController, type ActiveMove } from '../lib/movement';
import { POLL_MS, haversineM, type TruckState } from '../lib/trucks';
import { recortarRuta } from '../lib/route';
import { registrarMapa } from '../lib/mapHandle';
import { seguimientoDe } from '../state/seguimientoViaje';

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
 * Escala del marcador según el zoom. A zoom ciudad (12+) se dibuja a tamaño
 * completo; alejándose se achica hasta 55% para no tapar la provincia entera.
 * Nunca escala por encima de 1: crecer al acercarse solo tapa las calles.
 */
const PIN_FULL_ZOOM = OPEN_ZOOM;
const PIN_MIN_SCALE = 0.55;
const PIN_SCALE_PER_ZOOM = 0.09;

/* Ruta hasta la próxima parada, en azul para no confundirse con las calles. */
const ROUTE_COLOR = '#3f6fe0';
const ROUTE_WEIGHT = 6;
/*
 * Cuánto se puede alejar el camión de la ruta pedida antes de volver a pedirla.
 * Mientras siga cerca, la línea se recorta en su posición y no se gasta una
 * consulta al proveedor de ruteo en cada latido.
 */
const DESVIO_MAX_M = 120;
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
   * Encuadre al elegir un camión. En móvil (`true`) deja lugar a la hoja
   * inferior, que si no taparía el camión; en escritorio (`false`) vuela al
   * camión con el zoom de ciudad.
   */
  fitSelection?: boolean;
}

export default function MapView({
  onReady,
  showZoomControl = true,
  fitSelection = false,
}: MapViewProps = {}) {
  const { trucks, visibleTrucks, selectedId, select } = useDashboard();
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef(new Map<number, L.Marker>());
  /** Elementos del ícono de cada marcador: se actualizan en el lugar, sin setIcon. */
  const pinsRef = useRef(new Map<number, TruckPin>());
  /** Lo último aplicado a cada marcador, para saltear los camiones sin cambios. */
  const aplicadoRef = useRef(
    new Map<number, { truck: TruckState; seleccionado: boolean; visible: boolean }>(),
  );
  const lastPosRef = useRef(new Map<number, { lat: number; lng: number; updated: number }>());
  const movesRef = useRef(new Map<number, ActiveMove>());
  const movementRef = useRef<ReturnType<typeof createMovementController> | null>(null);
  const fittedRef = useRef(false);
  const trucksRef = useRef(trucks);
  const selectRef = useRef(select);
  /** Redibujo del viaje seleccionado, para llamarlo cuando se mueve el camión. */
  const redibujarViajeRef = useRef<(() => void) | null>(null);

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
    registrarMapa(map);
    onReady?.(map);
    const markers = markersRef.current;
    const pins = pinsRef.current;
    const aplicado = aplicadoRef.current;
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
      markers.clear();
      pins.clear();
      aplicado.clear();
      lastPos.clear();
      moves.clear();
      registrarMapa(null);
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

  /*
   * Reconcilia los marcadores con la flota, tocando sólo lo que cambió.
   *
   * `aplicarEstado` devuelve el mismo objeto para un camión que no cambió, así
   * que alcanza con comparar por identidad: si el camión, su selección y su
   * visibilidad son los mismos que en la pasada anterior, no se hace nada.
   * Antes cada latido recorría y reescribía todos los marcadores.
   */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const visibleIds = new Set(visibleTrucks.map((truck) => truck.id));
    const liveIds = new Set<number>();

    for (const truck of trucks) {
      if (truck.lat === null || truck.lng === null) continue;
      liveIds.add(truck.id);

      const seleccionado = truck.id === selectedId;
      const visible = visibleIds.has(truck.id);
      const aplicado = aplicadoRef.current.get(truck.id);
      if (
        aplicado &&
        aplicado.truck === truck &&
        aplicado.seleccionado === seleccionado &&
        aplicado.visible === visible
      ) {
        continue;
      }
      aplicadoRef.current.set(truck.id, { truck, seleccionado, visible });

      let marker = markersRef.current.get(truck.id);
      const pin = pinsRef.current.get(truck.id);
      if (!marker || !pin) {
        const nuevo = createTruckPin(truck, seleccionado);
        marker = L.marker([truck.lat, truck.lng], {
          icon: nuevo.icon,
          title: truck.plate,
        });
        marker.on('click', () => selectRef.current(truck.id));
        markersRef.current.set(truck.id, marker);
        pinsRef.current.set(truck.id, nuevo);
      } else {
        updateTruckPin(pin, truck, seleccionado);
      }
      /* El seleccionado queda arriba aunque otro camión pase por encima. */
      marker.setZIndexOffset(seleccionado ? 1000 : 0);

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

      if (visible) {
        if (!map.hasLayer(marker)) marker.addTo(map);
      } else {
        map.removeLayer(marker);
      }
    }

    for (const [id, marker] of markersRef.current) {
      if (liveIds.has(id)) continue;
      map.removeLayer(marker);
      markersRef.current.delete(id);
      pinsRef.current.delete(id);
      aplicadoRef.current.delete(id);
      lastPosRef.current.delete(id);
      movesRef.current.delete(id);
    }
  }, [trucks, visibleTrucks, selectedId]);

  /*
   * Dibujo del viaje abierto del camión seleccionado: las paradas numeradas y
   * la ruta desde donde está hasta la próxima.
   *
   * Las dos capas nacen en este efecto y mueren en su limpieza, que corre al
   * cambiar `selectedId`: nada de lo que dibuja una selección puede sobrevivir a
   * la siguiente.
   *
   * El viaje y la ruta salen del seguimiento compartido con el panel del camión
   * (`seguimientoViaje`): un solo polling por camión, en pausa con la pestaña
   * oculta. Acá sólo se dibuja: cuando cambia el viaje, y cuando el camión se
   * mueve, recortando el trazo en su posición. Si se aleja de la ruta, se le
   * pide al seguimiento que la vuelva a calcular.
   */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || selectedId === null) return;

    const id = selectedId;
    const seguimiento = seguimientoDe(id);
    const capaParadas = L.layerGroup().addTo(map);
    const capaRuta = L.layerGroup().addTo(map);

    /** Viaje ya pintado: el seguimiento conserva el objeto mientras no cambie. */
    let viajePintado: Trip | null | undefined;
    let destino: [number, number] | null = null;
    let puntosParadas: [number, number][] = [];
    let encuadrado = false;

    const posicionDelCamion = (): [number, number] | null => {
      const truck = trucksRef.current.find((t) => t.id === id);
      if (!truck || truck.lat === null || truck.lng === null) return null;
      return [truck.lat, truck.lng];
    };

    /*
     * Paradas del viaje, numeradas con su `seq`. La entregada se marca con un
     * check y baja de opacidad; la que se está visitando lleva el aro; la
     * próxima —primera `pending`, porque el viaje es secuencial— el halo.
     */
    const pintarParadas = (stops: TripStop[]) => {
      capaParadas.clearLayers();
      puntosParadas = [];
      const proxima = stops.find((stop) => stop.status === 'pending') ?? null;

      for (const stop of stops) {
        if (stop.lat === null || stop.lng === null) continue;
        puntosParadas.push([stop.lat, stop.lng]);
        const entregada = stop.status === 'delivered';
        const clases = [
          'stop-pin',
          entregada ? 'done' : '',
          stop.status === 'arrived' ? 'here' : '',
          stop === proxima ? 'target' : '',
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
          title: `Parada ${stop.seq}${entregada ? ' · entregada' : ''} — ${stop.address}`,
        }).addTo(capaParadas);
      }

      destino =
        proxima !== null && proxima.lat !== null && proxima.lng !== null
          ? [proxima.lat, proxima.lng]
          : null;
    };

    const dibujarRuta = (origen: [number, number] | null, tramo: [number, number][]) => {
      capaRuta.clearLayers();
      if (origen === null || destino === null) return;

      if (tramo.length < 2) {
        /* Sin proveedor de ruteo: recta punteada hasta la parada que toca. */
        L.polyline([origen, destino], {
          color: ROUTE_COLOR,
          weight: ROUTE_WEIGHT - 2,
          opacity: 0.85,
          dashArray: '9 7',
          lineCap: 'round',
        }).addTo(capaRuta);
        return;
      }

      /* El trazo arranca en el camión: si está a metros de la ruta, se une con
       * una recta corta en vez de dejar un hueco. */
      const { distancia, resto } = recortarRuta(tramo, origen[0], origen[1]);
      const puntos: [number, number][] = distancia > 5 ? [origen, ...resto] : resto;
      if (puntos.length < 2) return;
      L.polyline(puntos, {
        color: ROUTE_COLOR,
        weight: ROUTE_WEIGHT,
        opacity: 0.9,
        lineJoin: 'round',
        lineCap: 'round',
      }).addTo(capaRuta);
    };

    /* Móvil: camión y paradas tienen que quedar por encima de la hoja. */
    const encuadrar = (origen: [number, number] | null) => {
      if (!fitSelection || encuadrado) return;
      encuadrado = true;
      const puntos = origen ? [origen, ...puntosParadas] : puntosParadas;
      if (!puntos.length) return;
      map.fitBounds(L.latLngBounds(puntos), {
        paddingTopLeft: [24, 96],
        paddingBottomRight: [24, 240],
        maxZoom: 15,
        duration: 0.6,
      });
    };

    const dibujar = () => {
      const estado = seguimiento.getSnapshot();
      if (!estado.cargado) return;

      if (estado.viaje !== viajePintado) {
        viajePintado = estado.viaje;
        if (estado.viaje) {
          pintarParadas(estado.viaje.stops);
        } else {
          /* El viaje se cerró: no quedan pines de un viaje que ya terminó. */
          capaParadas.clearLayers();
          puntosParadas = [];
          destino = null;
        }
      }

      const origen = posicionDelCamion();
      const tramo = estado.ruta?.geometry ?? [];
      if (
        estado.viaje &&
        tramo.length > 1 &&
        origen !== null &&
        recortarRuta(tramo, origen[0], origen[1]).distancia > DESVIO_MAX_M
      ) {
        seguimiento.solicitarRuta();
      }
      dibujarRuta(origen, tramo);
      encuadrar(origen);
    };

    redibujarViajeRef.current = dibujar;
    const desuscribir = seguimiento.subscribe(dibujar);
    dibujar();

    return () => {
      desuscribir();
      if (redibujarViajeRef.current === dibujar) redibujarViajeRef.current = null;
      capaParadas.remove();
      capaRuta.remove();
    };
  }, [selectedId, fitSelection]);

  /* El camión se movió: el trazo se recorta en su nueva posición. */
  useEffect(() => {
    redibujarViajeRef.current?.();
  }, [trucks]);

  /*
   * Encuadre al elegir un camión (escritorio). El mapa puede estar oculto (el
   * shell móvil lo monta también en las secciones sin mapa y lo muestra con
   * `display:none`): con tamaño cero o zoom indefinido, `flyTo` proyecta NaN y
   * tumba la app. En ese caso se deja la vista como está.
   *
   * En móvil el encuadre lo hace el efecto del dibujo, que conoce las paradas
   * del viaje y les deja lugar a la hoja inferior.
   */
  useEffect(() => {
    if (selectedId === null || fitSelection) return;
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
