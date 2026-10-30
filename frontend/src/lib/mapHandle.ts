import type { Map as LeafletMap } from 'leaflet';

/*
 * Puente mínimo entre `MapView` y cualquier componente que necesite proyectar
 * coordenadas (por ejemplo, para colgar una tarjeta al lado del camión).
 *
 * El mapa lo monta el layout y vive una sola vez, así que alcanza con un
 * registro de módulo: no hay más de un mapa en pantalla y el que se desmonta
 * limpia la referencia.
 */
let actual: LeafletMap | null = null;

export function registrarMapa(map: LeafletMap | null): void {
  actual = map;
}

export function mapaActual(): LeafletMap | null {
  return actual;
}
