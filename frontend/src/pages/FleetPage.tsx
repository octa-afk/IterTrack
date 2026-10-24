import { useNavigate } from 'react-router-dom';
import { STATUS, ago, type SortKey, type TruckStatus } from '../lib/trucks';
import { useDashboard } from '../state/useDashboard';
import { TruckDetail } from '../components/TruckDetail';

/*
 * Camiones: la flota completa en tabla. Reusa el store y los filtros del
 * panel (búsqueda del topbar, estado, orden) en lugar de crear otro estado.
 * Usa `.fleet-page` y no `.grid`: el layout del panel es `display:contents`
 * para el mapa full-screen y dejaría esta tarjeta en la columna del sidebar.
 */
const CHIP_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'move', label: 'En movimiento' },
  { value: 'idle', label: 'Detenidos' },
  { value: 'stop', label: 'Apagados' },
] as const;

const COLUMNS: { key: SortKey | null; label: string; numeric?: boolean }[] = [
  { key: 'plate', label: 'Patente' },
  { key: null, label: 'Estado' },
  { key: 'speed', label: 'Velocidad', numeric: true },
  { key: 'updated', label: 'Último reporte' },
  { key: null, label: 'Rumbo', numeric: true },
  { key: null, label: '' },
];

export default function FleetPage() {
  const navigate = useNavigate();
  const { trucks, visibleTrucks, selectedId, filters, select, setFilter } = useDashboard();

  const ordenar = (key: SortKey) => {
    if (filters.sort === key) {
      setFilter({ dir: filters.dir === 'asc' ? 'desc' : 'asc' });
      return;
    }
    setFilter({ sort: key, dir: key === 'plate' ? 'asc' : 'desc' });
  };

  const verEnMapa = (id: number) => {
    select(id);
    navigate('/map');
  };

  return (
    <div className="fleet-page">
      <div className="card fleetcard">
        <div className="card-h">
          <h3>Camiones</h3>
          <span className="tag">
            {visibleTrucks.length} de {trucks.length}
          </span>
        </div>

        <div className="chips">
          {CHIP_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className="chip"
              aria-pressed={filters.status === opt.value}
              onClick={() => setFilter({ status: opt.value as 'all' | TruckStatus })}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="fleet-wrap">
          <table className="fleet-table">
            <thead>
              <tr>
                {COLUMNS.map((col) => {
                  const activa = col.key !== null && filters.sort === col.key;
                  return (
                    <th
                      key={col.label}
                      className={col.numeric ? 'num' : undefined}
                      aria-sort={
                        activa
                          ? filters.dir === 'asc'
                            ? 'ascending'
                            : 'descending'
                          : undefined
                      }
                    >
                      {col.key ? (
                        <button type="button" onClick={() => ordenar(col.key as SortKey)}>
                          {col.label}
                          <span aria-hidden="true">
                            {activa ? (filters.dir === 'asc' ? '▲' : '▼') : ''}
                          </span>
                        </button>
                      ) : (
                        col.label
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {!visibleTrucks.length && (
                <tr>
                  <td className="empty" colSpan={COLUMNS.length}>
                    Ningún camión coincide con los filtros.
                  </td>
                </tr>
              )}
              {visibleTrucks.map((truck) => (
                <tr
                  key={truck.id}
                  className={truck.id === selectedId ? 'sel' : undefined}
                  onClick={() => select(truck.id)}
                >
                  <td className="plate">
                    {truck.plate}
                    {!truck.active && <span className="badge-off">Inactivo</span>}
                  </td>
                  <td>
                    <span className="estado">
                      <span
                        className="dot"
                        style={{
                          background: truck.active
                            ? STATUS[truck.status].color
                            : 'var(--muted)',
                        }}
                      />
                      {truck.active ? STATUS[truck.status].label : 'Sin telemetría'}
                    </span>
                  </td>
                  <td className="num">
                    {truck.active && truck.updated ? `${truck.speed} km/h` : '—'}
                  </td>
                  <td>{truck.updated ? ago(truck.updated) : 'Sin señal'}</td>
                  <td className="num">{truck.updated ? `${truck.heading}°` : '—'}</td>
                  <td>
                    <button
                      type="button"
                      className="chip ver"
                      aria-label={`Ver ${truck.plate} en el mapa`}
                      onClick={(event) => {
                        event.stopPropagation();
                        verEnMapa(truck.id);
                      }}
                    >
                      Ver mapa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="col">
        <TruckDetail />
      </div>
    </div>
  );
}
