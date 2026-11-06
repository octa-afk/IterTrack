import L from 'leaflet';
import truckWebp from '../assets/truck.webp';
import type { TruckState } from './trucks';

/*
 * Marcador del camión con imagen WebP recortada (72x140, sin márgenes).
 * Se importa como asset para que Vite la emita en /assets, la única ruta de
 * archivos que sirve FastAPI en producción.
 * Gira con el rumbo del camión vía la variable CSS --heading;
 * el estado inactivo aplica grayscale desde el CSS (.pin.off .truck-img).
 */
type IconTruck = Pick<TruckState, 'status' | 'heading' | 'plate' | 'active'>;

const ICON_WIDTH = 32;
const ICON_HEIGHT = 62;

export function createTruckIcon(truck: IconTruck, selected: boolean): L.DivIcon {
  const pin = document.createElement('div');
  const classes = ['pin', truck.status, selected ? 'sel' : '', truck.active ? '' : 'off'];
  pin.className = classes.filter(Boolean).join(' ');
  pin.style.setProperty('--heading', `${truck.heading}deg`);

  const vehicle = document.createElement('img');
  vehicle.className = 'truck-img';
  vehicle.src = truckWebp;
  vehicle.alt = truck.plate;
  vehicle.style.display = 'block';

  const label = document.createElement('em');
  label.className = 'lbl';
  label.style.fontStyle = 'normal';
  label.textContent = truck.plate;

  pin.append(vehicle, label);
  return L.divIcon({
    className: '',
    iconSize: [ICON_WIDTH, ICON_HEIGHT],
    iconAnchor: [ICON_WIDTH / 2, ICON_HEIGHT / 2],
    html: pin,
  });
}
