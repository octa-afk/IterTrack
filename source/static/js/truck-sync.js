import { getTrucks } from './truck-api.js';
import { authHeaders, clearSessionAndRedirect } from './session.js';
import { getTruckList, setTrucks, getSelectedId, setSelectedId, getMarkers, getMoves } from './truck-store.js';

// Reconcile the organization-scoped truck list without resetting telemetry state.
export async function syncTrucks({ map, createTruckState }) {
  try {
    const res = await getTrucks(authHeaders());
    if (res.status === 401) {
      clearSessionAndRedirect();
      return false;
    }
    if (!res.ok) return false;
    const data = await res.json();
    const existing = new Map(getTruckList().map(truck => [truck.id, truck]));
    const currentIds = new Set(data.map(truck => truck.id));

    existing.forEach((truck, id) => {
      if (currentIds.has(id)) return;
      const marker = getMarkers().get(id);
      if (marker) map.removeLayer(marker);
      getMarkers().delete(id);
      getMoves().delete(id);
      if (getSelectedId() === id) setSelectedId(null);
    });

    setTrucks(data.map(truck => {
      const known = existing.get(truck.id);
      if (known) {
        known.plate = truck.plate;
        return known;
      }
      return createTruckState(truck);
    }));
    return true;
  } catch (error) {
    console.error('Error al cargar camiones:', error);
    return false;
  }
}
