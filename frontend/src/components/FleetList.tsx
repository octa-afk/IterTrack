import { STATUS, ago, type SortKey, type TruckStatus } from '../lib/trucks';
import { useDashboard } from '../state/useDashboard';

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
              <span className="dot" style={{ background: STATUS[truck.status].color }} />
              <span className="nm">{truck.plate}</span>
              <span className="sp">
                {truck.speed}
                <small> km/h</small>
              </span>
              <span className="sb">
                {[truck.driver, truck.updated ? ago(truck.updated) : 'Sin señal']
                  .filter(Boolean)
                  .join(' · ')}
              </span>
              <span className={'fu' + (truck.fuel != null && truck.fuel < 25 ? ' low' : '')}>
                {truck.fuel != null ? `${truck.fuel}% comb.` : '—'}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
