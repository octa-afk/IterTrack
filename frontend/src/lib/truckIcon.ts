import L from 'leaflet';
import type { TruckState } from './trucks';

/*
 * Ported verbatim from source/static/js/truck-marker.js.
 * The 36x54 truck glyph rotates with the heading via the --heading CSS var.
 */
const TRUCK_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 72" aria-hidden="true"><defs><filter id="map-shadow" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="2" stdDeviation="1.5" flood-color="#000000" flood-opacity="0.5" /></filter></defs><g filter="url(#map-shadow)" transform="translate(0, 4)"><rect x="8" y="30" width="32" height="36" rx="3" fill="#FFFFFF" stroke="#334155" stroke-width="2" /><rect x="12" y="34" width="24" height="28" rx="1" fill="#E2E8F0" /><rect x="22" y="26" width="4" height="6" fill="#1E293B" /><rect x="10" y="6" width="28" height="22" rx="4" fill="#2563EB" stroke="#1E3A8A" stroke-width="2" /><rect x="12" y="16" width="24" height="8" rx="2" fill="#020617" /><rect x="10" y="10" width="2" height="6" fill="#020617" /><rect x="36" y="10" width="2" height="6" fill="#020617" /><rect x="5" y="12" width="3" height="5" rx="1" fill="#020617" /><rect x="40" y="12" width="3" height="5" rx="1" fill="#020617" /><rect x="12" y="4" width="6" height="3" rx="1" fill="#F8FAFC" /><rect x="30" y="4" width="6" height="3" rx="1" fill="#F8FAFC" /></g></svg>`;

type IconTruck = Pick<TruckState, 'status' | 'heading' | 'plate'>;

export function createTruckIcon(truck: IconTruck, selected: boolean): L.DivIcon {
  const pin = document.createElement('div');
  pin.className = `pin ${truck.status} ${selected ? 'sel' : ''}`;
  const vehicle = document.createElement('span');
  vehicle.className = 'truck-svg';
  vehicle.style.setProperty('--heading', `${truck.heading}deg`);
  vehicle.innerHTML = TRUCK_SVG;
  const label = document.createElement('em');
  label.className = 'lbl';
  label.style.fontStyle = 'normal';
  label.textContent = truck.plate;
  pin.append(vehicle, label);
  return L.divIcon({ className: '', iconSize: [48, 48], iconAnchor: [24, 24], html: pin });
}
