/* Destinos y viajes. Contract: source/services/destinations.py. */
import { apiRequest } from './client';
import type { Charger, Depot, Trip, TripCreatePayload } from './types';

/** GET /chargers — dadores de carga de la organización. */
export function listChargers(): Promise<Charger[]> {
  return apiRequest<Charger[]>('/chargers');
}

/** GET /depots */
export function listDepots(): Promise<Depot[]> {
  return apiRequest<Depot[]>('/depots');
}

/** GET /trips — viajes de la organización, más reciente primero. */
export function listTrips(): Promise<Trip[]> {
  return apiRequest<Trip[]>('/trips');
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
