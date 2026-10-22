// Thin API boundary for the authenticated tracking dashboard.
// Response handling stays in map.js so existing state and error semantics remain unchanged.
export function getTrucks(headers) {
  return fetch('/trucks', { headers });
}

export function getLocation(truckId, headers) {
  return fetch(`/trucks/${truckId}/location`, { headers });
}

export function getHistory(truckId, headers) {
  return fetch(`/trucks/${truckId}/iter`, { headers });
}
