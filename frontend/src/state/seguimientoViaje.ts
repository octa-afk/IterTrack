import { useCallback, useSyncExternalStore } from 'react';
import { getTripRoute, listTrips } from '../api/destinations';
import type { Trip } from '../api/types';
import { indiceMasCercano, largoGeometria } from '../lib/route';
import { POLL_MS } from '../lib/trucks';
import { iniciarPolling, type Polling } from './polling';

/*
 * Viaje abierto y ruta hasta la próxima parada de un camión, compartidos.
 *
 * El mapa y el panel del camión necesitan lo mismo. Antes cada uno tenía su
 * polling: `listTrips` dos veces cada 3 s y la ruta (una consulta al proveedor
 * de ruteo) pedida dos veces por cada parada. Ahora hay un seguimiento por
 * camión, que existe mientras alguien lo mire y se apaga solo después.
 */

export interface RutaViaje {
  /** Geometría [lat, lng] hasta la próxima parada. */
  geometry: [number, number][];
  distance: number;
  duration: number;
  stopSeq: number;
  /** Largo de `geometry` en metros, para escalar distancia y tiempo restantes. */
  total: number;
}

export interface EstadoViaje {
  /** Ya llegó la primera respuesta de viajes. */
  cargado: boolean;
  /** Viaje abierto (`planned`/`in_progress`); `null` si no tiene. */
  viaje: Trip | null;
  /** Última ruta buena; se conserva mientras se pide una nueva. */
  ruta: RutaViaje | null;
  /** El último pedido de ruta falló o no hay proveedor de ruteo. */
  sinRuta: boolean;
}

export interface Seguimiento {
  subscribe(listener: () => void): () => void;
  getSnapshot(): EstadoViaje;
  /** El camión se alejó de la ruta: hay que pedirla de nuevo desde donde está. */
  solicitarRuta(): void;
}

/*
 * Espera tras un fallo del proveedor de ruteo. Sin esto un proveedor caído se
 * consulta en cada latido, lo que agrava el problema en vez de resolverlo.
 */
const REINTENTO_RUTA_MS = 15_000;

const INICIAL: EstadoViaje = { cargado: false, viaje: null, ruta: null, sinRuta: false };

const seguimientos = new Map<number, Seguimiento>();

/** Firma del viaje: si cambia, la ruta apunta a otra parada (o a otro lugar). */
function firmaDe(viaje: Trip): string {
  return `${viaje.id}|${viaje.stops
    .map((stop) => `${stop.id}:${stop.status}:${stop.lat}:${stop.lng}`)
    .join(',')}`;
}

function crearSeguimiento(truckId: number): Seguimiento {
  const listeners = new Set<() => void>();
  let estado = INICIAL;
  let polling: Polling | null = null;
  let firma = '';
  let hayQuePedir = false;
  let reintentarEn = 0;

  const publicar = (nuevo: EstadoViaje) => {
    if (
      nuevo.cargado === estado.cargado &&
      nuevo.viaje === estado.viaje &&
      nuevo.ruta === estado.ruta &&
      nuevo.sinRuta === estado.sinRuta
    ) {
      return;
    }
    estado = nuevo;
    listeners.forEach((listener) => listener());
  };

  async function latido() {
    const viajes = await listTrips(truckId).catch(() => null);
    if (viajes === null) return;

    const activo = viajes.find(
      (viaje) => viaje.status === 'planned' || viaje.status === 'in_progress',
    );
    if (!activo) {
      firma = '';
      hayQuePedir = false;
      publicar({ cargado: true, viaje: null, ruta: null, sinRuta: false });
      return;
    }

    let { ruta, sinRuta } = estado;
    let viaje = estado.viaje;
    const nuevaFirma = firmaDe(activo);
    if (nuevaFirma !== firma) {
      firma = nuevaFirma;
      viaje = activo;
      ruta = null;
      sinRuta = false;
      hayQuePedir = true;
      reintentarEn = 0;
    }

    /* La ruta apunta a la primera parada pendiente, como el backend. */
    const destino = activo.stops.find(
      (stop) => stop.status === 'pending' && stop.lat !== null && stop.lng !== null,
    );
    if (!destino) {
      hayQuePedir = false;
      ruta = null;
    } else if (hayQuePedir && Date.now() >= reintentarEn) {
      const nueva = await getTripRoute(activo.id).catch(() => null);
      if (nueva && nueva.geometry.length > 1) {
        /* Se corta en la parada: nunca se dibuja un tramo que la saltee. */
        const corte = indiceMasCercano(nueva.geometry, destino.lat!, destino.lng!);
        const geometry = nueva.geometry.slice(0, corte + 1);
        ruta = {
          geometry,
          distance: nueva.distance_m,
          duration: nueva.duration_s,
          stopSeq: nueva.stop_seq,
          total: largoGeometria(geometry),
        };
        sinRuta = false;
        hayQuePedir = false;
      } else {
        sinRuta = true;
        reintentarEn = Date.now() + REINTENTO_RUTA_MS;
      }
    }

    publicar({ cargado: true, viaje, ruta, sinRuta });
  }

  const seguimiento: Seguimiento = {
    subscribe(listener) {
      listeners.add(listener);
      if (listeners.size === 1) {
        seguimientos.set(truckId, seguimiento);
        polling = iniciarPolling(latido, POLL_MS);
      }
      return () => {
        listeners.delete(listener);
        if (listeners.size > 0) return;
        polling?.detener();
        polling = null;
        if (seguimientos.get(truckId) === seguimiento) seguimientos.delete(truckId);
      };
    },
    getSnapshot: () => estado,
    solicitarRuta() {
      if (hayQuePedir) return;
      hayQuePedir = true;
      polling?.ahora();
    },
  };
  return seguimiento;
}

/** El seguimiento del camión: el mismo objeto para todos los que lo miran. */
export function seguimientoDe(truckId: number): Seguimiento {
  let seguimiento = seguimientos.get(truckId);
  if (!seguimiento) {
    seguimiento = crearSeguimiento(truckId);
    seguimientos.set(truckId, seguimiento);
  }
  return seguimiento;
}

const sinSuscripcion = () => () => {};

/** Estado del viaje del camión para un componente; `null` sin camión. */
export function useSeguimientoViaje(truckId: number | null): EstadoViaje | null {
  const seguimiento = truckId === null ? null : seguimientoDe(truckId);
  const subscribe = useCallback(
    (listener: () => void) => (seguimiento ? seguimiento.subscribe(listener) : sinSuscripcion()),
    [seguimiento],
  );
  const getSnapshot = useCallback(
    () => (seguimiento ? seguimiento.getSnapshot() : null),
    [seguimiento],
  );
  return useSyncExternalStore(subscribe, getSnapshot);
}
