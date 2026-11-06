import { useEffect, useState } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { ApiError } from '../api/client';
import { listChargers, listTrips } from '../api/destinations';
import type { Charger, Trip } from '../api/types';
import { useDashboard } from '../state/useDashboard';
import type { MobileOutletContext } from './context';
import { Icon } from './icons';

const ESTADOS: Record<string, { label: string; color: string }> = {
  planned: { label: 'Planificado', color: '#F0A93B' },
  in_progress: { label: 'En curso', color: '#4F6BED' },
  done: { label: 'Finalizado', color: '#7A8091' },
  cancelled: { label: 'Cancelado', color: '#E0675C' },
};

const salida = (iso: string) =>
  new Date(iso).toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

/*
 * Rutas en móvil: los viajes reales de `GET /trips` con su dador de carga.
 * "Ver recorrido" es el mismo camino que en escritorio: enciende el trazo del
 * camión en el contexto y navega al panel, donde el mapa sigue montado.
 */
export default function MobileTripsPage() {
  const { role, trucks, verRecorrido } = useDashboard();
  const { openDrawer } = useOutletContext<MobileOutletContext>();
  const navigate = useNavigate();
  const [trips, setTrips] = useState<Trip[]>([]);
  const [chargers, setChargers] = useState<Charger[]>([]);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let cancelado = false;

    async function cargar() {
      try {
        const [viajes, dadores] = await Promise.all([listTrips(), listChargers()]);
        if (cancelado) return;
        setTrips(viajes);
        setChargers(dadores);
        setError('');
      } catch (fallo) {
        if (cancelado) return;
        setError(
          fallo instanceof ApiError ? fallo.message : 'No se pudieron cargar los viajes',
        );
      } finally {
        if (!cancelado) setCargando(false);
      }
    }

    void cargar();
    return () => {
      cancelado = true;
    };
  }, []);

  const nombreDador = (id: number) => chargers.find((c) => c.id === id)?.name ?? `#${id}`;
  const patente = (id: number | null) =>
    id === null ? '—' : (trucks.find((t) => t.id === id)?.plate ?? `#${id}`);

  const verRecorridoDelViaje = (truckId: number) => {
    verRecorrido(truckId);
    navigate('/map');
  };

  return (
    <section className="m-screen">
      <header className="m-appbar">
        <button
          className="m-btn-round"
          type="button"
          onClick={openDrawer}
          aria-label="Abrir menú"
        >
          <Icon name="menu" />
        </button>
        <h1>Viajes</h1>
        <span className="m-count">{trips.length}</span>
      </header>

      {error && <p className="m-aviso m-aviso--error">{error}</p>}

      <div className="m-list">
        {!cargando && !trips.length && !error && (
          <p className="m-empty">Todavía no hay viajes cargados.</p>
        )}

        {trips.map((trip) => {
          const estado = ESTADOS[trip.status] ?? { label: trip.status, color: '#7A8091' };
          return (
            <article className="m-card" key={trip.id}>
              <div className="m-card__head">
                <span className="m-dot" style={{ background: estado.color }} title={estado.label} />
                <span className="m-card__title">{nombreDador(trip.charger_id)}</span>
                <span className="m-card__meta">{salida(trip.departure_at)}</span>
              </div>
              <div className="m-card__grid">
                <div>
                  <div className="m-label">Camión</div>
                  <div className="m-value">{patente(trip.truck_id)}</div>
                </div>
                <div>
                  <div className="m-label">Destinos</div>
                  <div className="m-value">{trip.stops.length}</div>
                </div>
                <div className="m-card__heading">
                  <div className="m-label">Estado</div>
                  <div className="m-value">{estado.label}</div>
                </div>
              </div>
              {trip.truck_id !== null && (
                <button
                  className="m-btn-soft"
                  type="button"
                  onClick={() => verRecorridoDelViaje(trip.truck_id as number)}
                >
                  <Icon name="route" size={18} />
                  Ver recorrido
                </button>
              )}
            </article>
          );
        })}

        {role === 'member' && (
          <div className="m-notice">
            <span className="m-notice__icon">
              <Icon name="lock" size={20} />
            </span>
            <div>
              <h2>Nuevo viaje</h2>
              <p>
                Tu cuenta es de solo lectura. Para crear viajes necesitás una
                cuenta administradora de la organización.
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
