import L from 'leaflet';
import truckWebp from '../assets/truck.webp';
import type { TruckState } from './trucks';

/*
 * Marcador del camión con imagen WebP recortada (72x140, sin márgenes).
 * Se importa como asset para que Vite la emita en /assets, la única ruta de
 * archivos que sirve FastAPI en producción.
 * Gira con el rumbo del camión vía la variable CSS --heading;
 * el estado inactivo aplica grayscale desde el CSS (.pin.off .truck-img).
 *
 * El elemento se crea una sola vez por camión y después se actualiza en el
 * lugar. Antes se llamaba `setIcon` en cada polling: el DOM del marcador se
 * tiraba y se rehacía cada 3 s, la imagen podía parpadear y la transición de
 * giro nunca llegaba a verse porque el elemento nuevo nacía ya rotado.
 */
type IconTruck = Pick<TruckState, 'status' | 'heading' | 'plate' | 'active'>;

const ICON_WIDTH = 32;
const ICON_HEIGHT = 62;

export interface TruckPin {
  icon: L.DivIcon;
  pin: HTMLDivElement;
  vehicle: HTMLImageElement;
  label: HTMLElement;
  /** Último ángulo aplicado, sin recortar a 0–360 (ver `rumboContinuo`). */
  heading: number;
}

/**
 * Ángulo a aplicar para llegar a `nuevo` por el camino corto desde `anterior`.
 *
 * CSS interpola el número tal cual: de 350° a 10° giraría 340° hacia atrás.
 * Acumulando la diferencia mínima (350 → 370) el ícono gira sólo 20°.
 */
export function rumboContinuo(anterior: number, nuevo: number): number {
  const diferencia = ((((nuevo - anterior) % 360) + 540) % 360) - 180;
  return anterior + diferencia;
}

function clasesDe(truck: IconTruck, selected: boolean): string {
  return ['pin', truck.status, selected ? 'sel' : '', truck.active ? '' : 'off']
    .filter(Boolean)
    .join(' ');
}

export function createTruckPin(truck: IconTruck, selected: boolean): TruckPin {
  const pin = document.createElement('div');
  pin.className = clasesDe(truck, selected);
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
  /* Leaflet reusa este mismo `pin` cada vez que el marcador vuelve al mapa,
   * así que mutarlo alcanza aunque el marcador esté oculto por un filtro. */
  const icon = L.divIcon({
    className: '',
    iconSize: [ICON_WIDTH, ICON_HEIGHT],
    iconAnchor: [ICON_WIDTH / 2, ICON_HEIGHT / 2],
    html: pin,
  });
  return { icon, pin, vehicle, label, heading: truck.heading };
}

/** Aplica estado, selección, rumbo y patente sin recrear nada; sólo toca lo que cambió. */
export function updateTruckPin(marker: TruckPin, truck: IconTruck, selected: boolean): void {
  const clases = clasesDe(truck, selected);
  if (marker.pin.className !== clases) marker.pin.className = clases;

  const heading = rumboContinuo(marker.heading, truck.heading);
  if (heading !== marker.heading) {
    marker.heading = heading;
    marker.pin.style.setProperty('--heading', `${heading}deg`);
  }

  if (marker.label.textContent !== truck.plate) {
    marker.label.textContent = truck.plate;
    marker.vehicle.alt = truck.plate;
  }
}
