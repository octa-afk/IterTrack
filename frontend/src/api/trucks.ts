/* Tracking endpoints. Contract: source/services/tracking.py. */
import { apiRequest } from './client';
import type { TrackingPoint, Truck, TruckLive } from './types';

/** GET /trucks — trucks of the caller's organization. */
export function listTrucks(): Promise<Truck[]> {
  return apiRequest<Truck[]>('/trucks');
}

/** GET /trucks/live — la flota entera con el último punto de cada camión, en un pedido. */
export function listLiveTrucks(): Promise<TruckLive[]> {
  return apiRequest<TruckLive[]>('/trucks/live', { cache: 'no-store' });
}

/** GET /trucks/{id}/iter — history, newest first by measurement time. */
export function getHistory(truckId: number, limit?: number): Promise<TrackingPoint[]> {
  const query = limit === undefined ? '' : `?limit=${limit}`;
  return apiRequest<TrackingPoint[]>(`/trucks/${truckId}/iter${query}`);
}
