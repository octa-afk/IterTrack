import type { RefObject } from 'react';
import type { Map as LeafletMap } from 'leaflet';

/** Lo que el layout móvil comparte con sus pantallas. */
export interface MobileOutletContext {
  /** Mapa Leaflet ya montado; `null` hasta que `MapView` termina de crearlo. */
  map: RefObject<LeafletMap | null>;
  openDrawer: () => void;
}
