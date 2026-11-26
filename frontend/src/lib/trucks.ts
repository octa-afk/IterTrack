import type { TrackingPoint, Truck, TruckLive } from '../api/types';

/*
 * Pure helpers ported from the vanilla dashboard modules:
 *   source/static/js/{truck-store,truck-selection,truck-telemetry,truck-sync}.js
 * and the inline helpers in source/static/js/map.js.
 */

export type TruckStatus = 'move' | 'idle' | 'stop' | 'alert';
export interface TruckState {
  id: number;
  plate: string;
  color: string;
  /**
   * Fleet-lifecycle flag from the backend. An inactive truck keeps its history
   * but stops reporting: the UI must not present it as a live vehicle.
   */
  active: boolean;
  lat: number | null;
  lng: number | null;
  heading: number;
  status: TruckStatus;
  speed: number;
  fuel: number | null;
  driver: string;
  route: string;
  updated: number;
  history: number[];
}

export type SortKey = 'plate' | 'speed' | 'fuel' | 'updated' | 'driver';

export interface Filters {
  q: string;
  status: 'all' | TruckStatus;
  view: 'all' | 'alert';
  sort: SortKey;
  dir: 'asc' | 'desc';
}

export const DEFAULT_FILTERS: Filters = {
  q: '',
  status: 'all',
  view: 'all',
  sort: 'plate',
  dir: 'asc',
};

export const STATUS: Record<TruckStatus, { label: string }> = {
  move: { label: 'En movimiento' },
  idle: { label: 'Detenido' },
  stop: { label: 'Apagado' },
  alert: { label: 'Alerta' },
};

export const SPEED_LIMIT = 90;
export const FRESH_MS = 5 * 60e3;
export const HISTORY_MAX = 18;
export const POLL_MS = 3000;
/** Points requested from GET /trucks/{id}/iter for the detail sparkline. */
export const TRIP_LIMIT = 500;

const TRUCK_COLORS = [
  '#3f6fe0', '#2f9e6b', '#8b5cf0', '#0e93a8',
  '#d1468f', '#7a8b2e', '#e0a02f', '#d64545',
];

function hashTexto(s: string): number {
  let h = 0;
  for (const c of s) h = (h * 31 + (c.codePointAt(0) ?? 0)) >>> 0;
  return h;
}

export function colorDeCamion(t: { plate: string; id: number }): string {
  return TRUCK_COLORS[hashTexto(String(t.plate ?? t.id)) % TRUCK_COLORS.length];
}

export function ago(ms: number): string {
  const s = Math.max(0, Math.round((Date.now() - ms) / 1000));
  if (s < 60) return `hace ${s} s`;
  if (s < 3600) return `hace ${Math.round(s / 60)} min`;
  return `hace ${Math.round(s / 3600)} h`;
}

const RUMBOS = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'];

/** Punto cardinal (8 rumbos) del rumbo en grados, para el panel del camión. */
export function rumboCardinal(heading: number): string {
  const h = ((heading % 360) + 360) % 360;
  return RUMBOS[Math.round(h / 45) % 8];
}

/** True when the truck reported within the last five minutes ("Con señal"). */
export function isFresh(updated: number, now: number = Date.now()): boolean {
  return updated > 0 && now - updated < FRESH_MS;
}

export function crearEstadoCamion(t: Truck): TruckState {
  return {
    id: t.id,
    plate: t.plate,
    color: colorDeCamion(t),
    active: t.active,
    lat: null,
    lng: null,
    heading: 0,
    status: 'stop',
    speed: 0,
    fuel: null,
    driver: '',
    route: '',
    updated: 0,
    history: [],
  };
}

const toRad = (d: number) => (d * Math.PI) / 180;

export function haversineM(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6371e3;
  const dLat = toRad(bLat - aLat);
  const dLng = toRad(bLng - aLng);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/**
 * Aplica la foto de `GET /trucks/live` al estado del camión.
 *
 * Velocidad, rumbo y estado vienen calculados del servidor: antes se
 * reconstruían acá comparando dos posiciones, con la hora de llegada del punto
 * en vez de la de medición, y un lote guardado sin señal daba velocidades
 * absurdas.
 *
 * Devuelve **el mismo objeto** si no cambió nada visible. El mapa y React
 * comparan por identidad: un camión quieto no se vuelve a procesar.
 */
export function aplicarEstado(t: TruckState, live: TruckLive): TruckState {
  const updated = live.recorded_at ? Date.parse(live.recorded_at) || 0 : 0;
  const lat = live.lat;
  const lng = live.lng;
  const speed = Math.round(live.speed ?? 0);
  const heading = live.heading ?? t.heading;
  if (
    t.updated === updated &&
    t.lat === lat &&
    t.lng === lng &&
    t.speed === speed &&
    t.heading === heading &&
    t.status === live.status &&
    t.plate === live.plate &&
    t.active === live.active
  ) {
    return t;
  }
  /*
   * El polling repite la última posición mientras el equipo no reporta nada
   * nuevo: sólo una medición nueva suma una muestra a la gráfica.
   */
  const history =
    updated > t.updated ? [...t.history, speed].slice(-HISTORY_MAX) : t.history;
  return {
    ...t,
    plate: live.plate,
    active: live.active,
    lat,
    lng,
    speed,
    heading,
    status: live.status,
    updated,
    history,
  };
}

/** Velocidades informadas por el equipo, de la más vieja a la más nueva. */
export function buildHistory(points: TrackingPoint[]): number[] {
  return points
    .slice(0, HISTORY_MAX)
    .reverse()
    .map((point) => Math.round(point.speed));
}

/*
 * Cómo se lee una distancia y un tiempo de llegada en el panel. Un trayecto de
 * menos de un minuto igual se informa como "1 min": redondear a 0 haría pensar
 * que ya llegó.
 */
export function formatMinutes(seconds: number): string {
  const minutos = Math.max(1, Math.round(seconds / 60));
  if (minutos < 60) return `${minutos} min`;
  return `${Math.floor(minutos / 60)} h ${minutos % 60} min`;
}

export function formatDistance(meters: number): string {
  if (meters < 1000) return `${Math.round(meters / 10) * 10} m`;
  return `${(meters / 1000).toLocaleString('es-AR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} km`;
}

const normalize = (value: string) =>
  String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

export function filterAndSortTrucks(trucks: TruckState[], filters: Filters): TruckState[] {
  const query = normalize(filters.q.trim());
  const list = trucks.filter(
    (truck) =>
      (filters.view === 'all' || truck.status === 'alert') &&
      (filters.status === 'all' || truck.status === filters.status) &&
      (!query || normalize(`${truck.plate} ${truck.driver} ${truck.route}`).includes(query)),
  );
  const multiplier = filters.dir === 'asc' ? 1 : -1;
  list.sort((a, b) => {
    const left = a[filters.sort];
    const right = b[filters.sort];
    const result =
      typeof left === 'string'
        ? left.localeCompare(String(right), 'es')
        : (left as number) - (right as number);
    return result * multiplier;
  });
  return list;
}
