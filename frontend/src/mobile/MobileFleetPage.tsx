import { useNavigate, useOutletContext, useSearchParams } from 'react-router-dom';
import { STATUS, ago, rumboCardinal } from '../lib/trucks';
import { useDashboard } from '../state/useDashboard';
import type { MobileOutletContext } from './context';
import { Icon } from './icons';
import MobileTruckDetail from './MobileTruckDetail';

const FILTROS = [
  { value: 'all', label: 'Todos' },
  { value: 'move', label: 'En movimiento' },
  { value: 'idle', label: 'Detenidos' },
  { value: 'stop', label: 'Apagados' },
] as const;

/*
 * Camiones en móvil. El detalle usa `?truck=<id>` en lugar de una ruta propia
 * (por ejemplo `/fleet/:id`) porque FastAPI sólo sirve la SPA en `/fleet`: un
 * path nuevo daría 404 al recargar.
 */
export default function MobileFleetPage() {
  const [params] = useSearchParams();
  const truckId = Number(params.get('truck'));
  const { trucks, visibleTrucks, selectedId, filters, setFilter } = useDashboard();
  const { openDrawer } = useOutletContext<MobileOutletContext>();
  const navigate = useNavigate();

  if (params.get('truck') !== null && Number.isFinite(truckId)) {
    return <MobileTruckDetail id={truckId} />;
  }

  const cambiarFiltro = (status: (typeof FILTROS)[number]['value']) => {
    setFilter({ status, view: 'all' });
  };

  const ordenar = () => {
    setFilter({ sort: 'plate', dir: filters.dir === 'asc' ? 'desc' : 'asc' });
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
        <h1>Camiones</h1>
        <span className="m-count">
          {visibleTrucks.length} de {trucks.length}
        </span>
      </header>

      <div className="m-chips" role="group" aria-label="Filtrar por estado">
        {FILTROS.map((filtro) => (
          <button
            key={filtro.value}
            className="m-chip"
            type="button"
            aria-pressed={filters.status === filtro.value && filters.view === 'all'}
            onClick={() => cambiarFiltro(filtro.value)}
          >
            {filtro.label}
          </button>
        ))}
      </div>

      <div className="m-toolbar">
        <span>Ordenar por</span>
        <button type="button" onClick={ordenar}>
          Patente
          <span
            style={{ display: 'flex', transform: `rotate(${filters.dir === 'asc' ? 0 : 180}deg)` }}
          >
            <Icon name="chevronUp" size={16} />
          </span>
        </button>
      </div>

      <div className="m-list">
        {!visibleTrucks.length && (
          <p className="m-empty">No hay camiones con este estado.</p>
        )}
        {visibleTrucks.map((truck) => {
          const estado = truck.active
            ? STATUS[truck.status]
            : { label: 'Inactivo', color: 'var(--m-muted)' };
          return (
            <button
              key={truck.id}
              className={`m-card${truck.id === selectedId ? ' m-card--selected' : ''}`}
              type="button"
              onClick={() => navigate(`/fleet?truck=${truck.id}`)}
            >
              <div className="m-card__head">
                <span className="m-dot" style={{ background: estado.color }} />
                <span className="m-card__title">{truck.plate}</span>
                <span className="m-card__meta">{estado.label}</span>
                <Icon name="chevronRight" size={18} />
              </div>
              <div className="m-card__grid">
                <div>
                  <div className="m-label">Velocidad</div>
                  <div className="m-value">
                    <b>{truck.active && truck.status !== 'stop' ? truck.speed : '—'}</b> km/h
                  </div>
                </div>
                <div>
                  <div className="m-label">Último reporte</div>
                  <div className="m-value">
                    {truck.updated ? ago(truck.updated) : 'Sin señal'}
                  </div>
                </div>
                <div className="m-card__heading">
                  <div className="m-label">Rumbo</div>
                  <div className="m-value">
                    {truck.updated ? `${Math.round(truck.heading)}° ${rumboCardinal(truck.heading)}` : '—'}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
