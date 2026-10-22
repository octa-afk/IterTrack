/* Tracking endpoints. Contract: source/services/tracking.py. */
import { apiRequest } from './client';
import type { Location, TrackingPoint, Truck } from './types';

/** GET /trucks — trucks of the caller's organization. */
export function listTrucks(): Promise<Truck[]> {
  return apiRequest<Truck[]>('/trucks');
}

/** GET /trucks/{id}/location — most recent point by measurement time (404 if none). */
export function getLocation(truckId: number): Promise<TrackingPoint> {
  return apiRequest<TrackingPoint>(`/trucks/${truckId}/location`);
}

/** GET /trucks/{id}/iter — history, newest first by measurement time. */
export function getHistory(truckId: number, limit?: number): Promise<TrackingPoint[]> {
  const query = limit === undefined ? '' : `?limit=${limit}`;
  return apiRequest<TrackingPoint[]>(`/trucks/${truckId}/iter${query}`);
}

/** POST /trucks/{id}/location — append a new tracking point. */
export function updateLocation(truckId: number, location: Location): Promise<{ mensaje: string }> {
  return apiRequest<{ mensaje: string }>(`/trucks/${truckId}/location`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(location),
  });
}
