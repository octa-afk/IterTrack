/* Destinos y viajes. Contract: source/services/destinations.py. */
import { apiRequest } from './client';
import type { Charger, Depot, Trip, TripCreatePayload, TripRoute } from './types';

/** GET /chargers — dadores de carga de la organización. */
export function listChargers(): Promise<Charger[]> {
  return apiRequest<Charger[]>('/chargers');
}

/** POST /chargers — crea un dador de carga. */
export function createCharger(name: string): Promise<Charger> {
  return apiRequest<Charger>('/chargers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
}

/** GET /depots */
export function listDepots(): Promise<Depot[]> {
  return apiRequest<Depot[]>('/depots');
}

/** GET /trips — viajes de la organización, más reciente primero. */
export function listTrips(truckId?: number): Promise<Trip[]> {
  const query = truckId === undefined ? '' : `?truck_id=${truckId}`;
  return apiRequest<Trip[]>(`/trips${query}`);
}

/** GET /trips/available-trucks — activos y sin viaje abierto. */
export function listAvailableTrucks(): Promise<{ id: number; plate: string }[]> {
  return apiRequest<{ id: number; plate: string }[]>('/trips/available-trucks');
}

/** POST /trips — importa el viaje; el backend geocodifica los destinos. */
export function createTrip(payload: TripCreatePayload): Promise<Trip> {
  return apiRequest<Trip>('/trips', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/** GET /trips/{id}/route — ruta por calles desde el camión hasta las paradas. */
export function getTripRoute(tripId: number): Promise<TripRoute> {
  // Cambia con cada entrega y con cada metro del camión: nunca reusar caché.
  return apiRequest<TripRoute>(`/trips/${tripId}/route`, { cache: 'no-store' });
}
