import type { TrackingPoint, Truck } from '../api/types';

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
  const lng = p.lng;
  const ts = Date.parse(p.timestamp) || Date.now();
  /*
   * El polling repite la última posición mientras el equipo no reporta nada
   * nuevo. Sin este corte, cada vuelta empujaba una muestra idéntica a la
   * gráfica y en un minuto borraba el historial real.
   */
  const muestraNueva = ts > t.updated;
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
  if (muestraNueva) {
    t.history.push(t.speed);
    if (t.history.length > HISTORY_MAX) t.history.shift();
  }
  t.status = estadoDe(t);
}

export function buildHistory(points: TrackingPoint[]): number[] {
  const chronological = points.slice().reverse();
  const history: number[] = [];
  for (let i = 1; i < chronological.length; i++) {
    const current = chronological[i];
    const previous = chronological[i - 1];
    const seconds = (Date.parse(current.recorded_at) - Date.parse(previous.recorded_at)) / 1000;
    const distance = haversineM(previous.lat, previous.lng, current.lat, current.lng);
    history.push(seconds > 0 ? Math.max(0, Math.min(200, Math.round((distance / seconds) * 3.6))) : 0);
  }
  return history.slice(-HISTORY_MAX);
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
