import { useMemo } from 'react';
import { recortarRuta } from '../lib/route';
import { useSeguimientoViaje } from './seguimientoViaje';

/** Lo que falta hasta la próxima parada del viaje abierto del camión. */
export type NextStop =
  | { state: 'ok'; distanceM: number; durationS: number; stopSeq: number }
  /** El camión no tiene viaje abierto: no hay nada que mostrar. */
  | { state: 'no-trip' }
  /** Hay viaje, pero el proveedor de ruteo no devolvió tramo (sin ruta). */
  | { state: 'no-route' };

/*
 * Distancia y tiempo estimado hasta la próxima parada.
 *
 * El viaje y la ruta salen del seguimiento compartido con el mapa (un solo
 * polling por camión). Acá sólo se recorta la geometría en la posición del
 * camión y se escalan distancia y duración con el tramo que queda: el número
 * avanza con cada posición nueva sin volver a consultar al proveedor.
 */
export function useNextStop(
  truckId: number | null,
  lat: number | null,
  lng: number | null,
): NextStop | null {
  const estado = useSeguimientoViaje(truckId);

  return useMemo(() => {
    if (!estado || !estado.cargado) return null;
    if (!estado.viaje) return { state: 'no-trip' };
    const { ruta } = estado;
    if (!ruta || lat === null || lng === null) return { state: 'no-route' };

    const { largo } = recortarRuta(ruta.geometry, lat, lng);
    const ratio = ruta.total > 0 ? Math.min(1, largo / ruta.total) : 1;
    return {
      state: 'ok',
      distanceM: ruta.distance * ratio,
      durationS: ruta.duration * ratio,
      stopSeq: ruta.stopSeq,
    };
  }, [estado, lat, lng]);
}
