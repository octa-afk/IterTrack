import { haversineM } from './trucks';

/*
 * Geometría de la ruta por calles: la comparten el mapa (para dibujar el tramo
 * que falta) y el panel del camión (para saber cuánto queda hasta la parada).
 */

/** Largo de una polilínea, en metros. */
export function largoGeometria(geometry: [number, number][]): number {
  let total = 0;
  for (let i = 1; i < geometry.length; i += 1) {
    total += haversineM(
      geometry[i - 1][0],
      geometry[i - 1][1],
      geometry[i][0],
      geometry[i][1],
    );
  }
  return total;
}

export interface TramoRestante {
  /** Metros desde el camión hasta el punto más cercano de la ruta. */
  distancia: number;
  /** Puntos de la ruta desde el más cercano al camión hasta el destino. */
  resto: [number, number][];
  /** Largo total que falta: el desvío más el resto de la polilínea. */
  largo: number;
}

/*
 * Recorta la ruta en el punto más cercano al camión. OSRM devuelve la geometría
 * desde donde estaba el camión al pedirla; a los segundos ese origen queda atrás
 * y la línea arranca en una esquina que el camión ya pasó.
 */
export function recortarRuta(
  geometry: [number, number][],
  lat: number,
  lng: number,
): TramoRestante {
  let indice = 0;
  let distancia = Number.POSITIVE_INFINITY;
  geometry.forEach(([aLat, aLng], i) => {
    const d = haversineM(lat, lng, aLat, aLng);
    if (d < distancia) {
      distancia = d;
      indice = i;
    }
  });
  const resto = geometry.slice(indice);
  return { distancia, resto, largo: distancia + largoGeometria(resto) };
}
