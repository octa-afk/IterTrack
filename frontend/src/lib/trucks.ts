import type { TrackingPoint, Truck } from '../api/types';

/*
 * Pure helpers ported from the vanilla dashboard modules:
 *   source/static/js/{truck-store,truck-selection,truck-telemetry,truck-sync}.js
 * and the inline helpers in source/static/js/map.js.
 */

export type TruckStatus = 'move' | 'idle' | 'stop' | 'alert';

/** A recorded position of the selected truck's recent trail. */
export interface PathPoint {
  lat: number;
  lng: number;
  /** Measurement time in ms (from `recorded_at`). */
  at: number;
}

export interface TripSummary {
  km: number;
  minutes: number;
  points: number;
}

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
  /** Recent trail, oldest first. Empty until the truck is selected. */
  path: PathPoint[];
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

export const STATUS: Record<TruckStatus, { label: string; color: string }> = {
  move: { label: 'En movimiento', color: '#5a7ee6' },
  idle: { label: 'Detenido', color: '#eeb04a' },
  stop: { label: 'Apagado', color: '#8a949c' },
  alert: { label: 'Alerta', color: '#e0675c' },
};

export const SPEED_LIMIT = 90;
export const STALE_MS = 10 * 60e3;
export const FRESH_MS = 5 * 60e3;
export const HISTORY_MAX = 18;
export const POLL_MS = 3000;
/** Points requested from GET /trucks/{id}/iter for the map trail. */
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

/** True when the truck reported within the last five minutes ("Con señal"). */
export function isFresh(updated: number, now: number = Date.now()): boolean {
  return updated > 0 && now - updated < FRESH_MS;
}

export function estadoDe(t: Pick<TruckState, 'updated' | 'speed'>): TruckStatus {
  if (!t.updated) return 'stop';
  if (Date.now() - t.updated > STALE_MS) return 'stop';
  if (t.speed > SPEED_LIMIT) return 'alert';
  if (t.speed < 3) return 'idle';
  return 'move';
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
    path: [],
  };
}

const toRad = (d: number) => (d * Math.PI) / 180;
const toDeg = (r: number) => (r * 180) / Math.PI;

export function haversineM(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6371e3;
  const dLat = toRad(bLat - aLat);
  const dLng = toRad(bLng - aLng);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export function bearing(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const y = Math.sin(toRad(bLng - aLng)) * Math.cos(toRad(bLat));
  const x =
    Math.cos(toRad(aLat)) * Math.sin(toRad(bLat)) -
    Math.sin(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.cos(toRad(bLng - aLng));
  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

/** Mutates `t` in place (same as the vanilla aplicarPunto). */
export function aplicarPunto(t: TruckState, p: TrackingPoint): void {
  const lat = p.lat;
  const lng = p.long;
  const ts = Date.parse(p.timestamp) || Date.now();
  if (t.lat !== null && t.lng !== null) {
    const dtMs = ts - t.updated;
    const distance = haversineM(t.lat, t.lng, lat, lng);
    if (dtMs > 0) {
      t.speed = Math.max(0, Math.min(200, Math.round((distance / (dtMs / 1000)) * 3.6)));
    }
    if (distance > 5) t.heading = bearing(t.lat, t.lng, lat, lng);
  }
  t.lat = lat;
  t.lng = lng;
  t.updated = ts;
  t.history.push(t.speed);
  if (t.history.length > HISTORY_MAX) t.history.shift();
  t.status = estadoDe(t);
}

export function buildHistory(points: TrackingPoint[]): number[] {
  const chronological = points.slice().reverse();
  const history: number[] = [];
  for (let i = 1; i < chronological.length; i++) {
    const current = chronological[i];
    const previous = chronological[i - 1];
    const seconds = (Date.parse(current.recorded_at) - Date.parse(previous.recorded_at)) / 1000;
    const distance = haversineM(previous.lat, previous.long, current.lat, current.long);
    history.push(seconds > 0 ? Math.max(0, Math.min(200, Math.round((distance / seconds) * 3.6))) : 0);
  }
  return history.slice(-HISTORY_MAX);
}

/**
 * Chronological trail from GET /trucks/{id}/iter (newest first).
 *
 * Consecutive identical positions are dropped: a parked truck reports the same
 * coordinates repeatedly and they would add nothing to the drawn line.
 */
/*
 * Cierre de vuelta. El camión sale a dar la vuelta a un circuito y, al pasar de
 * nuevo por el punto de partida, la vuelta terminó: lo dibujado hasta ahí era
 * una vuelta completa y lo que siga es otra. Sin esto el trazado se superpone
 * consigo mismo y el resumen suma kilómetros de dos vueltas.
 *
 * El radio tolera el error del GPS; el mínimo evita cerrar la vuelta en el
 * primer punto (donde la distancia al inicio es cero por definición).
 */
export const LAP_RADIUS_M = 60;
export const LAP_MIN_M = 1000;

/** Recorta el recorrido para dejar sólo la vuelta en curso. */
export function keepCurrentLap(path: PathPoint[]): PathPoint[] {
  if (path.length < 2) return path;
  let start = 0;
  let meters = 0;
  for (let i = 1; i < path.length; i++) {
    meters += haversineM(path[i - 1].lat, path[i - 1].lng, path[i].lat, path[i].lng);
    const volvioAlInicio =
      meters >= LAP_MIN_M &&
      haversineM(path[start].lat, path[start].lng, path[i].lat, path[i].lng) <=
        LAP_RADIUS_M;
    if (volvioAlInicio) {
      start = i;
      meters = 0;
    }
  }
  return start === 0 ? path : path.slice(start);
}

export function buildPath(points: TrackingPoint[]): PathPoint[] {
  const chronological = points.slice().reverse();
  const path: PathPoint[] = [];
  for (const point of chronological) {
    const at = Date.parse(point.recorded_at) || Date.now();
    const last = path[path.length - 1];
    if (last && last.lat === point.lat && last.lng === point.long) {
      path[path.length - 1] = { ...last, at };
      continue;
    }
    path.push({ lat: point.lat, lng: point.long, at });
  }
  return keepCurrentLap(path.slice(-TRIP_LIMIT));
}

/** Append a freshly polled location to an already seeded trail. */
export function appendPath(path: PathPoint[], point: TrackingPoint): PathPoint[] {
  if (!path.length) return path;
  const at = Date.parse(point.recorded_at) || Date.now();
  const last = path[path.length - 1];
  if (at <= last.at) return path;
  if (last.lat === point.lat && last.lng === point.long) {
    return [...path.slice(0, -1), { ...last, at }];
  }
  return [...path, { lat: point.lat, lng: point.long, at }].slice(-TRIP_LIMIT);
}

/**
 * Velocidad que ningún camión alcanza. Por encima de esto dos puntos seguidos
 * no son un recorrido: son un corte (el simulador reinició en otro punto del
 * circuito, el equipo se reasignó, el GPS saltó). Unirlos dibuja una recta que
 * cruza la ciudad y que el camión nunca hizo.
 */
export const MAX_TRAIL_KMH = 200;

/** Velocidad implícita entre dos puntos del recorrido, en km/h. */
function impliedKmh(first: PathPoint, second: PathPoint): number {
  const seconds = (second.at - first.at) / 1000;
  const meters = haversineM(first.lat, first.lng, second.lat, second.lng);
  if (seconds <= 0) return meters > 0 ? Number.POSITIVE_INFINITY : 0;
  return (meters / seconds) * 3.6;
}

/** True cuando el tramo entre dos puntos es un corte, no un recorrido. */
export function isTrailJump(
  first: PathPoint,
  second: PathPoint,
  maxKmh = MAX_TRAIL_KMH,
): boolean {
  return impliedKmh(first, second) > maxKmh;
}

/**
 * Parte el recorrido donde hay un corte.
 *
 * El mapa dibuja un segmento por tramo continuo: sin esto, un solo corte
 * atraviesa el recorrido con una recta larga. Un tramo de un solo punto no se
 * dibuja (no hay línea que trazar).
 */
export function splitPath(path: PathPoint[], maxKmh = MAX_TRAIL_KMH): PathPoint[][] {
  const segments: PathPoint[][] = [];
  let current: PathPoint[] = [];
  for (const point of path) {
    const last = current[current.length - 1];
    if (last && isTrailJump(last, point, maxKmh)) {
      if (current.length > 1) segments.push(current);
      current = [];
    }
    current.push(point);
  }
  if (current.length > 1) segments.push(current);
  return segments;
}

/** Distance and duration of a trail; null when there is nothing to measure. */
export function tripSummary(path: PathPoint[]): TripSummary | null {
  // Sólo el último tramo continuo: si hubo un corte, el resumen del recorrido
  // actual no puede sumar kilómetros de un trazado anterior.
  const segments = splitPath(path);
  const current = segments[segments.length - 1];
  if (!current || current.length < 2) return null;
  let meters = 0;
  for (let i = 1; i < current.length; i++) {
    meters += haversineM(current[i - 1].lat, current[i - 1].lng, current[i].lat, current[i].lng);
  }
  const minutes = Math.max(0, (current[current.length - 1].at - current[0].at) / 60000);
  return { km: meters / 1000, minutes, points: current.length };
}

/** Compact duration for the trip summary: 45 min, 2.3 h. */
export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)} min`;
  return `${(minutes / 60).toFixed(1)} h`;
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
