/* Tracking endpoints. Contract: source/services/tracking.py. */
import { apiRequest } from './client';
import type { TrackingPoint, Truck } from './types';

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
