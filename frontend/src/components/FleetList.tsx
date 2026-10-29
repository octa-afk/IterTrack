import { STATUS, ago, type SortKey, type TruckStatus } from '../lib/trucks';
import { useDashboard } from '../state/useDashboard';
import { FleetSearch } from './FleetSearch';

const SEG_OPTIONS = [
  { value: 'all', label: 'Toda la flota' },
  { value: 'alert', label: 'Solo alertas' },
] as const;

const CHIP_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'move', label: 'En movimiento' },
  { value: 'idle', label: 'Detenidos' },
  { value: 'stop', label: 'Apagados' },
] as const;

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'plate', label: 'Patente' },
  { value: 'speed', label: 'Velocidad' },
  { value: 'fuel', label: 'Combustible' },
  { value: 'updated', label: 'Última señal' },
  { value: 'driver', label: 'Chofer' },
];

export function FleetList() {
  const { trucks, visibleTrucks, selectedId, filters, select, setFilter } = useDashboard();

  return (
    <div className="card listcard">
      <FleetSearch />

      <div className="seg" id="seg">
        {SEG_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            data-v={opt.value}
            aria-pressed={filters.view === opt.value}
            onClick={() => setFilter({ view: opt.value })}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="chips" id="chips">
        {CHIP_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className="chip"
            data-s={opt.value}
            aria-pressed={filters.status === opt.value}
            onClick={() => setFilter({ status: opt.value as 'all' | TruckStatus })}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="sorts">
        <select
          id="sort"
          aria-label="Ordenar por"
          value={filters.sort}
          onChange={(e) => setFilter({ sort: e.target.value as SortKey })}
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          id="dir"
          aria-label="Dirección del orden"
          value={filters.dir}
          onChange={(e) => setFilter({ dir: e.target.value as 'asc' | 'desc' })}
        >
          <option value="asc">Ascendente</option>
          <option value="desc">Descendente</option>
        </select>
      </div>

      <div className="count" id="count">
        {visibleTrucks.length} de {trucks.length} camiones
      </div>

      <ul id="list">
        {!visibleTrucks.length && (
          <li className="empty">Ningún camión coincide con los filtros.</li>
        )}
        {visibleTrucks.map((truck) => (
          <li key={truck.id} className={truck.id === selectedId ? 'sel' : undefined}>
            <button type="button" onClick={() => select(truck.id)}>
              <span
                className="dot"
                style={{
                  background: truck.active ? STATUS[truck.status].color : 'var(--muted)',
                }}
              />
              <span className="nm">
                {truck.plate}
                {!truck.active && <span className="badge-off">Inactivo</span>}
              </span>
              <span className="sp">
                {truck.active && truck.status !== 'stop' ? truck.speed : '—'}
                <small> km/h</small>
              </span>
              <span className="sb">
                {[
                  truck.active ? STATUS[truck.status].label : 'Apagado',
                  truck.updated ? ago(truck.updated) : 'Sin señal',
                ].join(' · ')}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
