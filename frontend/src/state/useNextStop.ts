import { useEffect, useRef, useState } from 'react';
import { getTripRoute, listTrips } from '../api/destinations';
import { largoGeometria, recortarRuta } from '../lib/route';
import { POLL_MS } from '../lib/trucks';

/** Lo que falta hasta la próxima parada del viaje abierto del camión. */
export type NextStop =
  | { state: 'ok'; distanceM: number; durationS: number; stopSeq: number }
  /** El camión no tiene viaje abierto: no hay nada que mostrar. */
  | { state: 'no-trip' }
  /** Hay viaje, pero el proveedor de ruteo no devolvió tramo (sin ruta). */
  | { state: 'no-route' };

interface RutaActiva {
  geometry: [number, number][];
  distance: number;
  duration: number;
  stopSeq: number;
  total: number;
}

/*
 * Distancia y tiempo estimado hasta la próxima parada.
 *
 * La ruta por calles se pide una sola vez por parada. Entre medio se recorta la
 * geometría en la posición del camión y se escala la distancia y la duración con
 * el tramo que queda: el número avanza con cada latido sin golpear al proveedor
 * cada tres segundos.
 */
export function useNextStop(
  truckId: number | null,
  lat: number | null,
  lng: number | null,
): NextStop | null {
  const [actual, setActual] = useState<{ truckId: number; stop: NextStop } | null>(null);
  const posRef = useRef<{ lat: number | null; lng: number | null }>({ lat, lng });

  useEffect(() => {
    posRef.current = { lat, lng };
  }, [lat, lng]);

  useEffect(() => {
    if (truckId === null) return;

    let cancelado = false;
    /** Firma de estados de las paradas: si cambia, la ruta apunta a otra. */
    let firma = '';
    let pedida = false;
    let ruta: RutaActiva | null = null;

    const id = truckId;

    async function tick() {
      const viajes = await listTrips(id).catch(() => null);
      if (cancelado || viajes === null) return;

      const activo = viajes.find(
        (viaje) => viaje.status === 'planned' || viaje.status === 'in_progress',
      );
      if (!activo) {
        firma = '';
        pedida = false;
        ruta = null;
        setActual({ truckId: id, stop: { state: 'no-trip' } });
        return;
      }

      const estado = activo.stops.map((stop) => stop.status).join('');
      if (estado !== firma) {
        firma = estado;
        pedida = false;
        ruta = null;
      }

      if (!pedida) {
        pedida = true;
        const nueva = await getTripRoute(activo.id).catch(() => null);
        if (cancelado) return;
        ruta =
          nueva && nueva.geometry.length > 1
            ? {
                geometry: nueva.geometry,
                distance: nueva.distance_m,
                duration: nueva.duration_s,
                stopSeq: nueva.stop_seq,
                total: largoGeometria(nueva.geometry),
              }
            : null;
      }

      const { lat: la, lng: ln } = posRef.current;
      if (!ruta || la === null || ln === null) {
        setActual({ truckId: id, stop: { state: 'no-route' } });
        return;
      }

      const { largo } = recortarRuta(ruta.geometry, la, ln);
      const ratio = ruta.total > 0 ? Math.min(1, largo / ruta.total) : 1;
      setActual({
        truckId: id,
        stop: {
          state: 'ok',
          distanceM: ruta.distance * ratio,
          durationS: ruta.duration * ratio,
          stopSeq: ruta.stopSeq,
        },
      });
    }

    void tick();
    const interval = window.setInterval(() => {
      void tick();
    }, POLL_MS);

    return () => {
      cancelado = true;
      window.clearInterval(interval);
    };
  }, [truckId]);

  return actual && actual.truckId === truckId ? actual.stop : null;
}
