import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { STATUS, ago, formatDistance, formatMinutes, rumboCardinal } from '../lib/trucks';
import { useDashboard } from '../state/useDashboard';
import { useNextStop } from '../state/useNextStop';
import { Sparkline } from '../components/Sparkline';
import { Icon } from './icons';

/*
 * Detalle del camión (`/fleet?truck=<id>`). Se reusa el mismo contexto que el
 * resto: `select` trae el historial real para el gráfico y `useNextStop` da la
 * distancia y el tiempo hasta la próxima parada del viaje abierto.
 */
export default function MobileTruckDetail({ id }: { id: number }) {
  const { trucks, ready, select } = useDashboard();
  const navigate = useNavigate();
  const truck = trucks.find((item) => item.id === id) ?? null;
  const nextStop = useNextStop(truck?.id ?? null, truck?.lat ?? null, truck?.lng ?? null);

  // `select` escribe el historial sobre la flota ya cargada: si se llama antes
  // del primer refresh del provider, `prev` está vacío y el resultado se
  // descarta. Por eso se espera a `ready`.
  const selectRef = useRef(select);
  const pedidoRef = useRef<number | null>(null);
  useEffect(() => {
    selectRef.current = select;
  });
  useEffect(() => {
    if (!ready || pedidoRef.current === id) return;
    pedidoRef.current = id;
    selectRef.current(id);
  }, [id, ready]);

  const estado = truck
    ? truck.active
      ? STATUS[truck.status]
      : { label: 'Inactivo', color: 'var(--m-muted)' }
    : null;

  return (
    <section className="m-screen">
      <header className="m-appbar">
        <button
          className="m-btn-round"
          type="button"
          onClick={() => navigate('/fleet')}
          aria-label="Volver a camiones"
        >
          <Icon name="back" />
        </button>
        <div className="m-appbar__text">
          <h1>{truck?.plate ?? (ready ? 'No encontrado' : 'Cargando…')}</h1>
          {truck && estado && (
            <div className="m-appbar__sub">
              {estado.label} · {truck.updated ? ago(truck.updated) : 'Sin señal'}
            </div>
          )}
        </div>
      </header>

      {truck ? (
        <>
          <div className="m-stats">
            <div className="m-stat">
              <div className="m-label">Velocidad (km/h)</div>
              <div className="m-stat__value m-stat__value--big">
                {truck.active && truck.status !== 'stop' ? truck.speed : '—'}
              </div>
            </div>
            <div className="m-stat">
              <div className="m-label">Combustible</div>
              <div className="m-stat__value">
                {truck.fuel != null ? `${truck.fuel}%` : '—'}
              </div>
            </div>
            <div className="m-stat">
              <div className="m-label">Chofer</div>
              <div className="m-stat__value">{truck.driver || '—'}</div>
            </div>
            <div className="m-stat">
              <div className="m-label">Rumbo</div>
              <div className="m-stat__value">
                {truck.updated ? (
                  <>
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="var(--m-accent)"
                      style={{ transform: `rotate(${truck.heading}deg)` }}
                      aria-hidden="true"
                    >
                      <path d="M12 2.5l7.5 19-7.5-4.4-7.5 4.4z" />
                    </svg>
                    {Math.round(truck.heading)}° {rumboCardinal(truck.heading)}
                  </>
                ) : (
                  '—'
                )}
              </div>
            </div>
          </div>

          <div className="m-row-card">
            <span>Próxima parada</span>
            <span>
              {nextStop?.state === 'ok'
                ? `${formatDistance(nextStop.distanceM)} · ${formatMinutes(nextStop.durationS)}`
                : nextStop?.state === 'no-route'
                  ? 'Sin ruta disponible'
                  : 'Sin viaje abierto'}
            </span>
          </div>

          <div className="m-chart">
            <p>Velocidad reciente</p>
            {truck.history.length > 1 ? (
              <Sparkline data={truck.history} />
            ) : (
              <p className="m-empty">Todavía no hay suficientes reportes.</p>
            )}
          </div>

          <button
            className="m-btn-dark m-cta"
            type="button"
            onClick={() => {
              select(id);
              navigate('/map');
            }}
          >
            <Icon name="pin" size={20} />
            Ver en el mapa
          </button>
        </>
      ) : (
        <p className="m-empty">Ese camión no está en tu flota.</p>
      )}
    </section>
  );
}
